"""Entidade principal inimiga, com ataques, ULTs e escalonamento por fase."""

from __future__ import annotations

import math
from pathlib import Path
import pygame

from entities.entity import Entity
from entities.projectile import Projectile
from entities.ult_strike import UltStrike
from utils.constants import (
    BOSS_COLOR,
    BOSS_HEAL_PAUSE,
    BOSS_MOVE_RANGE,
    BOSS_MOVE_SPEED,
    BOSS_PROJECTILE_COLOR,
    BOSS_PROJECTILE_SPEED,
    HEIGHT,
    MINION_MAX_ALIVE,
    MINION_SPAWN_COOLDOWN,
    BOSS_ULT_COOLDOWN,
    BOSS_ULT_DAMAGE,
    WIDTH,
)


class Boss(Entity):
    """Boss central da arena com progressao continua e cura em fases."""

    SPRITE_FRAME_COUNT = 10
    SPRITE_FRAME_DURATION = 0.09
    SPRITE_DRAW_SIZE = (150, 150)
    SPRITE_SHEET_PATH = Path(__file__).resolve().parent.parent / "assets" / "boss_sheet.png"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, 90, 90, max_hp=220)
        self.float_origin_x = x
        self.float_origin_y = y
        self.float_time = 0.0
        self._is_immortal = True
        self.attack_cooldown = 1.5
        self.attack_timer = 0.4
        self.projectile_damage = 10
        self.telegraph_window = 0.4
        self.heal_pause_timer = 0.0
        self.ult_timer = 5.0
        self.ult_index = 0
        self.phase = 1
        self.ult_damage = BOSS_ULT_DAMAGE
        self.minion_spawn_timer = 4.0
        self.animation_timer = 0.0
        self.current_frame = 0
        self.sprite_frames = self._load_sprite_frames()

    def update(self, dt: float, player: Entity) -> None:
        """Atualiza timers e movimento, exceto durante a pausa de cura."""
        self._update_animation(dt)
        self.heal_pause_timer = max(0.0, self.heal_pause_timer - dt)

        if self.heal_pause_timer > 0:
            return

        self.float_time += dt
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.ult_timer = max(0.0, self.ult_timer - dt)
        self.minion_spawn_timer = max(0.0, self.minion_spawn_timer - dt)
        # Movimento oscilante simples: adiciona dificuldade sem transformar o boss em uma IA complexa.
        self.rect.x = int(self.float_origin_x + math.sin(self.float_time * BOSS_MOVE_SPEED) * BOSS_MOVE_RANGE)
        self.rect.y = int(self.float_origin_y + math.sin(self.float_time * 2) * 18)

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha o boss e um brilho quando ele esta se recuperando."""
        if self.sprite_frames:
            frame = self.sprite_frames[self.current_frame]
            sprite_rect = frame.get_rect(center=self.rect.center)
            screen.blit(frame, sprite_rect)
        else:
            pygame.draw.ellipse(screen, BOSS_COLOR, self.rect)

        if self.heal_pause_timer > 0:
            overlay_size = self.sprite_frames[0].get_size() if self.sprite_frames else self.rect.size
            overlay = pygame.Surface(overlay_size, pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 85))
            overlay_rect = overlay.get_rect(center=self.rect.center)
            screen.blit(overlay, overlay_rect)

    def is_healing(self) -> bool:
        """Indica se o boss esta travado na pausa de cura."""
        return self.heal_pause_timer > 0

    def draw_telegraph(self, screen: pygame.Surface, player: Entity) -> None:
        """Desenha aviso visual antes do disparo basico do boss."""
        if self.heal_pause_timer > 0:
            return

        if self.attack_timer > self.telegraph_window:
            return

        # Avisa o disparo sem complicar a IA: linha e anel mais fortes perto do tiro.
        ratio = 1.0 - (self.attack_timer / self.telegraph_window if self.telegraph_window else 0.0)
        alpha = int(70 + 120 * ratio)
        radius = int(56 + 10 * ratio)

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.line(overlay, (255, 120, 120, alpha), self.rect.center, player.rect.center, 2)
        pygame.draw.circle(overlay, (255, 140, 140, alpha), self.rect.center, radius, 2)
        screen.blit(overlay, (0, 0))

    def take_damage(self, amount: int) -> int:
        """Consome HP visivel e aciona cura/fase nova quando zera."""
        if self.heal_pause_timer > 0:
            return 0

        # O boss perde vida visualmente, mas "renasce" com a barra cheia quando zera.
        dealt = super().take_damage(amount)
        if self._is_immortal and self.hp <= 0:
            self.advance_phase()
            self.hp = self.max_hp
            self.heal_pause_timer = BOSS_HEAL_PAUSE
            self.attack_timer = self.attack_cooldown
            self.ult_timer = max(self.ult_timer, 2.0)
        return dealt

    def try_attack(self, player: Entity) -> Projectile | None:
        """Dispara o ataque basico se o cooldown estiver liberado."""
        if self.heal_pause_timer > 0:
            return None

        if self.attack_timer > 0:
            return None

        # O boss atira no centro do player para manter o comportamento previsivel.
        self.attack_timer = self.attack_cooldown
        return Projectile(
            self.rect.centerx,
            self.rect.centery,
            player.rect.centerx,
            player.rect.centery,
            damage=self.projectile_damage,
            speed=BOSS_PROJECTILE_SPEED,
            color=BOSS_PROJECTILE_COLOR,
            size=(16, 16),
        )

    def try_ult(self, player: Entity) -> list[UltStrike]:
        """Seleciona e instancia a proxima ULT do ciclo."""
        if self.heal_pause_timer > 0:
            return []

        if self.ult_timer > 0:
            return []

        self.ult_timer = BOSS_ULT_COOLDOWN
        pattern = self.ult_index % 3
        self.ult_index += 1

        if pattern == 0:
            return self._target_burst(player)
        if pattern == 1:
            return self._arena_lanes()
        return self._crusher_pattern(player)

    def should_spawn_minion(self, current_alive: int) -> bool:
        """Decide se o boss pode invocar mais capangas voadores agora."""
        if self.heal_pause_timer > 0:
            return False

        if current_alive >= self.get_max_aerial_minions():
            return False

        if self.minion_spawn_timer > 0:
            return False

        self.minion_spawn_timer = max(3.8, MINION_SPAWN_COOLDOWN - self.phase * 0.25)
        return True

    def get_max_aerial_minions(self) -> int:
        """Retorna o limite de capangas voadores simultaneos para a fase atual."""
        return min(MINION_MAX_ALIVE, 1 + self.phase // 2)

    def get_minion_spawn_positions(self) -> list[tuple[int, int]]:
        """Retorna dois pontos de spawn na metade superior da arena."""
        left_x = max(70, self.rect.centerx - 230)
        right_x = min(WIDTH - 70, self.rect.centerx + 230)
        y = min(HEIGHT // 2 - 40, self.rect.y + 80)
        return [(left_x, y), (right_x, y)]

    def _target_burst(self, player: Entity) -> list[UltStrike]:
        # ULT 1: pressiona a posicao do player com colunas laterais para punir movimento curto.
        strikes: list[UltStrike] = []
        for offset in (-150, 0, 150):
            x = max(60, min(WIDTH - 60, player.rect.centerx + offset))
            strikes.append(UltStrike(x, 46, self.ult_damage))
        return strikes

    def _arena_lanes(self) -> list[UltStrike]:
        # ULT 2: fecha lanes fixas da arena inteira. E forte, mas previsivel.
        strikes: list[UltStrike] = []
        for ratio in (0.14, 0.30, 0.46, 0.62, 0.78, 0.90):
            strikes.append(UltStrike(int(WIDTH * ratio), 38, self.ult_damage))
        return strikes

    def _crusher_pattern(self, player: Entity) -> list[UltStrike]:
        # ULT 3: fecha o espaco em torno do player com uma parede mais densa.
        strikes: list[UltStrike] = []
        for offset in (-240, -120, 0, 120, 240):
            x = max(50, min(WIDTH - 50, player.rect.centerx + offset))
            strikes.append(UltStrike(x, 34, self.ult_damage + 4))
        return strikes

    def scale_up(self) -> None:
        """Escalonamento por tempo, independente das fases por cura."""
        self.projectile_damage += 1
        self.attack_cooldown = max(0.55, self.attack_cooldown - 0.08)

    def advance_phase(self) -> None:
        """Escalonamento maior aplicado cada vez que a barra do boss zera."""
        # Cada "morte" deixa o boss um pouco mais resistente e agressivo.
        self.phase += 1
        self.max_hp += 22
        self.projectile_damage += 2
        self.ult_damage += 2
        self.attack_cooldown = max(0.45, self.attack_cooldown - 0.05)

    def _load_sprite_frames(self) -> list[pygame.Surface]:
        """Carrega e fatia o spritesheet do boss quando o asset estiver disponivel."""
        if not self.SPRITE_SHEET_PATH.exists():
            return []

        sheet = pygame.image.load(str(self.SPRITE_SHEET_PATH)).convert_alpha()
        frame_width = sheet.get_width() // self.SPRITE_FRAME_COUNT
        frame_height = sheet.get_height()
        frames: list[pygame.Surface] = []

        for index in range(self.SPRITE_FRAME_COUNT):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), pygame.Rect(index * frame_width, 0, frame_width, frame_height))
            frames.append(pygame.transform.scale(frame, self.SPRITE_DRAW_SIZE))

        return frames

    def _update_animation(self, dt: float) -> None:
        """Avanca a animacao do boss em loop enquanto o jogo roda."""
        if not self.sprite_frames:
            return

        self.animation_timer += dt
        while self.animation_timer >= self.SPRITE_FRAME_DURATION:
            self.animation_timer -= self.SPRITE_FRAME_DURATION
            self.current_frame = (self.current_frame + 1) % len(self.sprite_frames)
