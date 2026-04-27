"""Entidade controlada pelo jogador."""

from __future__ import annotations

import math
from pathlib import Path

import pygame

from entities.entity import Entity
from entities.projectile import Projectile
from skills.dash import Dash
from skills.shield import Shield
from skills.shot import Shot
from utils.constants import (
    GRAVITY,
    GROUND_Y,
    PLAYER_COLOR,
    PLAYER_JUMP_SPEED,
    PLAYER_SPEED,
    WIDTH,
)


class Player(Entity):
    """Controla movimento, recursos, skills e dano recebido pelo player.

    A hitbox logica do personagem permanece pequena e previsivel para o
    combate, enquanto o sprite pode ser maior para melhorar a leitura visual.
    """

    SPRITE_SHEET_PATH = Path(__file__).resolve().parent.parent / "assets" / "player" / "knight_spritesheet.png"
    SPRITE_CELL_SIZE = 64
    SPRITE_RENDER_SIZE = (96, 96)
    DASH_ANIMATION_DURATION = 0.18
    SPRITE_ROWS = {
        "idle": (0, 4, 5.0),
        "walk": (1, 6, 10.0),
        "jump": (2, 6, 9.0),
        "shield": (3, 6, 12.0),
        "dash": (4, 6, 14.0),
    }
    _sprite_frames: dict[str, list[pygame.Surface]] | None = None

    def __init__(self, x: float, y: float) -> None:
        """Inicializa atributos de mobilidade, recursos e animacao."""
        super().__init__(x, y, 50, 80, max_hp=100)
        self.velocity_y = 0.0
        self.on_ground = False
        self.aura = 0
        self.max_aura = 100
        self.aura_threshold = 100
        self.shot = Shot()
        self.dash = Dash()
        self.shield = Shield()
        self.invulnerability_timer = 0.0
        self.dash_animation_timer = 0.0
        self.facing = 1
        self.move_direction = 0
        self.animation_time = 0.0

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        """Aplica movimento, gravidade, cooldowns e timers defensivos.

        O player usa simulacao simples de plataforma: deslocamento horizontal
        direto, velocidade vertical acumulada e colisao apenas com o plano do
        chao.
        """
        direction = 0

        if keys[pygame.K_a]:
            direction -= 1
        if keys[pygame.K_d]:
            direction += 1

        self.move_direction = direction
        if direction != 0:
            # A ultima direcao horizontal valida e reaproveitada pelo dash e
            # tambem define o flip do sprite do personagem.
            self.facing = int(math.copysign(1, direction))
            self.dash.last_direction = self.facing

        self.rect.x += int(direction * PLAYER_SPEED * dt)
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))

        if keys[pygame.K_w] and self.on_ground:
            self.velocity_y = PLAYER_JUMP_SPEED
            self.on_ground = False

        self.velocity_y += GRAVITY * dt
        self.rect.y += int(self.velocity_y * dt)

        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.velocity_y = 0
            self.on_ground = True

        if self.invulnerability_timer > 0:
            self.invulnerability_timer = max(0.0, self.invulnerability_timer - dt)

        self.shot.update(dt)
        self.dash.update(dt)
        self.shield.update(dt)
        self.animation_time += dt
        if self.dash_animation_timer > 0:
            self.dash_animation_timer = max(0.0, self.dash_animation_timer - dt)

        if self.shield.active_timer > 0:
            self.shield.active_timer = max(0.0, self.shield.active_timer - dt)

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha o player e o efeito visual do escudo quando ativo."""
        if self.shield.active_timer > 0:
            pygame.draw.circle(screen, (120, 180, 255), self.rect.center, 40, 3)

        frames = self._get_sprite_frames()
        state = self._get_animation_state()
        state_frames = frames.get(state)

        if not state_frames:
            color = (255, 255, 255) if self.invulnerability_timer > 0 else PLAYER_COLOR
            pygame.draw.rect(screen, color, self.rect)
            return

        # Cada estado tem sua propria velocidade de animacao para reforcar a
        # sensacao de peso do personagem.
        _, _, fps = self.SPRITE_ROWS[state]
        frame_index = int(self.animation_time * fps) % len(state_frames)
        sprite = state_frames[frame_index]

        if self.facing < 0:
            sprite = pygame.transform.flip(sprite, True, False)

        if self.invulnerability_timer > 0:
            sprite = sprite.copy()
            sprite.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_ADD)

        draw_rect = sprite.get_rect(midbottom=(self.rect.centerx, self.rect.bottom + 4))
        screen.blit(sprite, draw_rect)

    def use_shot(self, target_position: tuple[int, int]) -> Projectile | None:
        """Dispara um projetil na direcao do cursor, se o cooldown permitir."""
        if not self.shot.is_ready():
            return None

        self.shot.activate()
        spawn_x = self.rect.centerx
        spawn_y = self.rect.centery
        return Projectile(spawn_x, spawn_y, target_position[0], target_position[1], damage=self.shot.damage)

    def gain_aura(self, amount: int) -> None:
        """Acumula aura ate o limite maximo."""
        self.aura = min(self.max_aura, self.aura + amount)

    def aura_ready(self) -> bool:
        """Indica quando a barra atingiu o limiar de upgrade."""
        return self.aura >= self.aura_threshold

    def use_dash(self) -> None:
        """Executa um deslocamento curto na ultima direcao horizontal usada.

        O dash atual e instantaneo: ele nao cria uma fase de fisica propria,
        apenas teletransporta o rect alguns pixels e deixa um timer visual.
        """
        if not self.dash.is_ready():
            return

        self.dash.activate()
        self.dash_animation_timer = self.DASH_ANIMATION_DURATION
        direction = self.dash.last_direction or 1
        self.facing = direction
        self.rect.x += direction * self.dash.distance
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))

    def use_shield(self) -> None:
        """Ativa imunidade temporaria se o shield estiver disponivel."""
        if not self.shield.is_ready():
            return

        self.shield.activate()

    def apply_upgrade(self, kind: str) -> None:
        """Aplica um upgrade simples e reseta a barra de aura.

        Os upgrades foram mantidos pequenos e cumulativos para que o impacto
        seja legivel sem exigir uma arvore de progressao complexa.
        """
        if kind == "damage":
            self.shot.damage += 4
        elif kind == "cooldown":
            self.shot.cooldown = max(0.10, self.shot.cooldown - 0.05)
        elif kind == "shield":
            self.shield.duration += 0.4

        self.aura = 0

    def take_damage(self, amount: int) -> int:
        """Ignora dano durante i-frames ou shield ativo."""
        if self.invulnerability_timer > 0 or self.shield.active_timer > 0:
            return 0

        self.invulnerability_timer = 0.5
        return super().take_damage(amount)

    def _get_animation_state(self) -> str:
        """Escolhe a linha da spritesheet com base no estado de movimento atual.

        A ordem dos testes importa: dash e shield sobrescrevem estados mais
        genericos porque representam momentos especiais de gameplay.
        """
        if self.dash_animation_timer > 0:
            return "dash"
        if self.shield.active_timer > 0:
            return "shield"
        if not self.on_ground:
            return "jump"
        if self.move_direction != 0:
            return "walk"
        return "idle"

    @classmethod
    def _get_sprite_frames(cls) -> dict[str, list[pygame.Surface]]:
        """Carrega e fatia a spritesheet do player uma unica vez.

        O cache em classe evita recarregar o mesmo asset sempre que uma nova
        run comeca.
        """
        if cls._sprite_frames is not None:
            return cls._sprite_frames

        if not cls.SPRITE_SHEET_PATH.exists():
            cls._sprite_frames = {}
            return cls._sprite_frames

        sheet = pygame.image.load(str(cls.SPRITE_SHEET_PATH)).convert_alpha()
        frames: dict[str, list[pygame.Surface]] = {}

        for state, (row, frame_count, _) in cls.SPRITE_ROWS.items():
            row_frames: list[pygame.Surface] = []
            for index in range(frame_count):
                frame = pygame.Surface((cls.SPRITE_CELL_SIZE, cls.SPRITE_CELL_SIZE), pygame.SRCALPHA)
                area = pygame.Rect(
                    index * cls.SPRITE_CELL_SIZE,
                    row * cls.SPRITE_CELL_SIZE,
                    cls.SPRITE_CELL_SIZE,
                    cls.SPRITE_CELL_SIZE,
                )
                frame.blit(sheet, (0, 0), area)
                row_frames.append(pygame.transform.scale(frame, cls.SPRITE_RENDER_SIZE))
            frames[state] = row_frames

        cls._sprite_frames = frames
        return cls._sprite_frames
