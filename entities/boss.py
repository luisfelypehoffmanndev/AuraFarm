"""Entidade principal inimiga, com ataques, ULTs e escalonamento por fase."""

from __future__ import annotations

from pathlib import Path

import math
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
    """Boss central da arena com progressao continua e cura em fases.

    O combate contra o boss e o eixo central do jogo. Por isso a classe guarda
    tanto comportamento ofensivo quanto politicas de escalonamento e de spawn
    de ameacas auxiliares.
    """

    SPRITE_FRAME_COUNT = 10
    SPRITE_FRAME_DURATION = 0.09
    SPRITE_DRAW_SIZE = (150, 150)
    SPRITE_SHEET_PATH = Path(__file__).resolve().parent.parent / "assets" / "boss_sheet.png"
    HEAL_FRAME_COUNT = 8
    HEAL_SPRITE_SHEET_PATH = Path(__file__).resolve().parent.parent / "assets" / "effects" / "heal_spritesheet.png"
    ATTACK_FRAME_COUNT = 10
    ATTACK_SPRITE_SHEET_PATH = Path(__file__).resolve().parent.parent / "assets" / "effects" / "attack_spritesheet.png"
    PROJECTILE_SPRITE_SHEET_PATH = str(
        Path(__file__).resolve().parent.parent / "assets" / "projectiles" / "bola_energia_spritesheet_4x.png"
    )
    PROJECTILE_FRAME_COUNT = 8

    def __init__(self, x: float, y: float) -> None:
        """Inicializa a fase inicial, timers de combate e assets animados."""
        super().__init__(x, y, 90, 90, max_hp=220)
        self.float_origin_x = x
        self.float_origin_y = y
        self.float_time = 0.0
        self._is_immortal = True
        self.attack_cooldown = 1.9
        self.attack_timer = 1.1
        self.projectile_damage = 8
        self.telegraph_window = 0.55
        self.heal_pause_timer = 0.0
        self.ult_timer = 11.0
        self.ult_index = 0
        self.phase = 1
        self.ult_damage = BOSS_ULT_DAMAGE
        self.minion_spawn_timer = 8.0
        self.animation_timer = 0.0
        self.current_frame = 0
        self.special_attack_timer = 0.0
        self.sprite_frames = self._load_sprite_frames()
        self.heal_frames = self._load_heal_frames()
        self.attack_frames = self._load_attack_frames()

    def update(self, dt: float, player: Entity) -> None:
        """Atualiza timers e movimento, exceto durante a pausa de cura.

        O parametro ``player`` e mantido na assinatura porque o boss participa
        do mesmo contrato de update usado pelo coordenador do jogo, embora a
        logica de movimento atual nao dependa dele diretamente.
        """
        self._update_animation(dt)
        self.heal_pause_timer = max(0.0, self.heal_pause_timer - dt)
        self.special_attack_timer = max(0.0, self.special_attack_timer - dt)

        if self.heal_pause_timer > 0:
            return

        self.float_time += dt
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.ult_timer = max(0.0, self.ult_timer - dt)
        self.minion_spawn_timer = max(0.0, self.minion_spawn_timer - dt)
        # O movimento oscilante faz o boss ocupar mais espaco visual sem exigir
        # uma IA espacial complexa.
        self.rect.x = int(self.float_origin_x + math.sin(self.float_time * BOSS_MOVE_SPEED) * BOSS_MOVE_RANGE)
        self.rect.y = int(self.float_origin_y + math.sin(self.float_time * 2) * 18)

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha o boss no estado visual correspondente ao momento atual."""
        if self.heal_pause_timer > 0 and self.heal_frames:
            frame = self.heal_frames[self.current_frame % len(self.heal_frames)]
            screen.blit(frame, frame.get_rect(center=self.rect.center))
            return

        if self.special_attack_timer > 0 and self.attack_frames:
            frame = self.attack_frames[self.current_frame % len(self.attack_frames)]
            screen.blit(frame, frame.get_rect(center=self.rect.center))
            return

        if self.sprite_frames:
            frame = self.sprite_frames[self.current_frame]
            sprite_rect = frame.get_rect(center=self.rect.center)
            screen.blit(frame, sprite_rect)
        else:
            pygame.draw.ellipse(screen, BOSS_COLOR, self.rect)

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
        """Consome HP visivel e aciona cura/fase nova quando zera.

        O boss atual funciona como inimigo de sobrevivencia: ele nao entra em
        estado final de morte, mas evolui de fase cada vez que a barra esvazia.
        """
        if self.heal_pause_timer > 0:
            return 0

        # O HP mostrado esvazia normalmente, mas a luta continua em nova fase.
        dealt = super().take_damage(amount)
        if self._is_immortal and self.hp <= 0:
            self.advance_phase()
            self.hp = self.max_hp
            self.heal_pause_timer = BOSS_HEAL_PAUSE
            self.attack_timer = self.attack_cooldown
            self.ult_timer = max(self.ult_timer, min(7.0, self.get_ult_cooldown() * 0.5))
        return dealt

    def try_attack(self, player: Entity) -> Projectile | None:
        """Dispara o ataque basico se o cooldown estiver liberado."""
        if self.heal_pause_timer > 0:
            return None

        if self.attack_timer > 0:
            return None

        # Mirar no centro do player torna o ataque justo e legivel.
        self.attack_timer = self.attack_cooldown
        return Projectile(
            self.rect.centerx,
            self.rect.centery,
            player.rect.centerx,
            player.rect.centery,
            damage=self.projectile_damage,
            speed=BOSS_PROJECTILE_SPEED,
            color=BOSS_PROJECTILE_COLOR,
            size=(30, 30),
            sprite_sheet_path=self.PROJECTILE_SPRITE_SHEET_PATH,
            sprite_frame_count=self.PROJECTILE_FRAME_COUNT,
            sprite_size=(56, 56),
            animation_fps=14.0,
        )

    def try_ult(self, player: Entity) -> list[UltStrike]:
        """Seleciona e instancia a proxima ULT do ciclo.

        O padrao gira em ciclos de tres para criar variacao previsivel e ainda
        assim permitir que o jogador aprenda a luta.
        """
        if self.heal_pause_timer > 0:
            return []

        if self.ult_timer > 0:
            return []

        self.ult_timer = self.get_ult_cooldown()
        self.special_attack_timer = self.SPRITE_FRAME_DURATION * len(self.attack_frames)
        self.animation_timer = 0.0
        self.current_frame = 0
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

        self.minion_spawn_timer = self.get_minion_spawn_cooldown()
        return True

    def get_max_aerial_minions(self) -> int:
        """Retorna o limite de capangas voadores simultaneos para a fase atual."""
        return min(MINION_MAX_ALIVE, max(0, self.phase // 2))

    def get_ult_cooldown(self) -> float:
        """A ULT comeca mais espacada e acelera de forma perceptivel por fase."""
        return max(8.0, BOSS_ULT_COOLDOWN - (self.phase - 1) * 1.15)

    def get_minion_spawn_cooldown(self) -> float:
        """Invocacoes entram depois da fase inicial e escalam mais forte no meio da run."""
        return max(5.2, MINION_SPAWN_COOLDOWN - (self.phase - 1) * 0.85)

    def get_minion_spawn_positions(self) -> list[tuple[int, int]]:
        """Retorna dois pontos de spawn na metade superior da arena."""
        left_x = max(70, self.rect.centerx - 230)
        right_x = min(WIDTH - 70, self.rect.centerx + 230)
        y = min(HEIGHT // 2 - 40, self.rect.y + 80)
        return [(left_x, y), (right_x, y)]

    def _target_burst(self, player: Entity) -> list[UltStrike]:
        """Cria uma ULT focada na posicao atual do player."""
        # ULT 1: pressiona a posicao do player com colunas laterais para punir movimento curto.
        strikes: list[UltStrike] = []
        for offset in (-150, 0, 150):
            x = max(60, min(WIDTH - 60, player.rect.centerx + offset))
            strikes.append(UltStrike(x, 46, self.ult_damage))
        return strikes

    def _arena_lanes(self) -> list[UltStrike]:
        """Cria uma ULT de lanes fixas distribuida pela arena."""
        # ULT 2: fecha lanes fixas da arena inteira. E forte, mas previsivel.
        strikes: list[UltStrike] = []
        for ratio in (0.14, 0.30, 0.46, 0.62, 0.78, 0.90):
            strikes.append(UltStrike(int(WIDTH * ratio), 38, self.ult_damage))
        return strikes

    def _crusher_pattern(self, player: Entity) -> list[UltStrike]:
        """Cria uma ULT mais densa comprimindo o espaco do player."""
        # ULT 3: fecha o espaco em torno do player com uma parede mais densa.
        strikes: list[UltStrike] = []
        for offset in (-240, -120, 0, 120, 240):
            x = max(50, min(WIDTH - 50, player.rect.centerx + offset))
            strikes.append(UltStrike(x, 34, self.ult_damage + 4))
        return strikes

    def scale_up(self) -> None:
        """Aplica o escalonamento leve ativado pelo tempo de sobrevivencia."""
        self.projectile_damage += 1
        self.attack_cooldown = max(0.65, self.attack_cooldown - 0.10)

    def advance_phase(self) -> None:
        """Aplica o escalonamento forte de uma nova fase do boss."""
        # Cada "morte" deixa o boss um pouco mais resistente e agressivo.
        self.phase += 1
        self.max_hp += 34
        self.projectile_damage += 2
        self.ult_damage += 3
        self.attack_cooldown = max(0.55, self.attack_cooldown - 0.08)

    def _load_sprite_frames(self) -> list[pygame.Surface]:
        """Carrega e fatia o spritesheet do boss quando o asset estiver disponivel."""
        if not self.SPRITE_SHEET_PATH.exists():
            return []

        return self._load_sheet_frames(self.SPRITE_SHEET_PATH, self.SPRITE_FRAME_COUNT, self.SPRITE_DRAW_SIZE)

    def _load_heal_frames(self) -> list[pygame.Surface]:
        """Carrega os frames do boss em estado de cura."""
        if not self.HEAL_SPRITE_SHEET_PATH.exists():
            return []

        return self._load_sheet_frames(self.HEAL_SPRITE_SHEET_PATH, self.HEAL_FRAME_COUNT, self.SPRITE_DRAW_SIZE)

    def _load_attack_frames(self) -> list[pygame.Surface]:
        """Carrega os frames do boss durante o ataque especial."""
        if not self.ATTACK_SPRITE_SHEET_PATH.exists():
            return []

        return self._load_sheet_frames(self.ATTACK_SPRITE_SHEET_PATH, self.ATTACK_FRAME_COUNT, self.SPRITE_DRAW_SIZE)

    def _load_sheet_frames(
        self,
        sheet_path: Path,
        frame_count: int,
        draw_size: tuple[int, int],
    ) -> list[pygame.Surface]:
        """Fatia um spritesheet horizontal em frames escalados.

        O projeto usa spritesheets em linha unica para simplificar a pipeline
        de animacao dos atores principais.
        """
        sheet = pygame.image.load(str(sheet_path)).convert_alpha()
        frame_width = sheet.get_width() // frame_count
        frame_height = sheet.get_height()
        frames: list[pygame.Surface] = []

        for index in range(frame_count):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), pygame.Rect(index * frame_width, 0, frame_width, frame_height))
            frames.append(pygame.transform.scale(frame, draw_size))

        return frames

    def _update_animation(self, dt: float) -> None:
        """Avanca a animacao do boss em loop enquanto o jogo roda."""
        if self.heal_pause_timer > 0 and self.heal_frames:
            active_frames = self.heal_frames
        elif self.special_attack_timer > 0 and self.attack_frames:
            active_frames = self.attack_frames
        else:
            active_frames = self.sprite_frames

        if not active_frames:
            return

        self.animation_timer += dt
        while self.animation_timer >= self.SPRITE_FRAME_DURATION:
            self.animation_timer -= self.SPRITE_FRAME_DURATION
            self.current_frame = (self.current_frame + 1) % len(active_frames)
