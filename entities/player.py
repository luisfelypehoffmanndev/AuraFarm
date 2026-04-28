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
    WEAPON_SHEET_PATH = Path(__file__).resolve().parent.parent / "assets" / "player" / "crossbow_sheet.png"
    SPRITE_CELL_SIZE = 64
    SPRITE_RENDER_SIZE = (96, 96)
    WEAPON_CELL_SIZE = 16
    WEAPON_FRAME_COUNT = 6
    WEAPON_RENDER_SIZE = (52, 28)
    WEAPON_ANIMATION_FPS = 20.0
    DART_RENDER_SIZE = (28, 10)
    DASH_ANIMATION_DURATION = 0.18
    SPRITE_ROWS = {
        "idle": (0, 4, 5.0),
        "walk": (1, 6, 10.0),
        "jump": (2, 6, 9.0),
        "shield": (3, 6, 12.0),
        "dash": (4, 6, 14.0),
    }
    _sprite_frames: dict[str, list[pygame.Surface]] | None = None
    _weapon_frames: list[pygame.Surface] | None = None
    _dart_surface: pygame.Surface | None = None

    def __init__(self, x: float, y: float) -> None:
        """Inicializa atributos de mobilidade, recursos e animacao."""
        super().__init__(x, y, 50, 80, max_hp=100)
        self.velocity_y = 0.0
        self.on_ground = False
        self.aura = 0
        self.max_aura = 100
        self.aura_threshold = 100
        self.total_aura_collected = 0
        self.shot = Shot()
        self.dash = Dash()
        self.shield = Shield()
        self.invulnerability_timer = 0.0
        self.dash_animation_timer = 0.0
        self.facing = 1
        self.move_direction = 0
        self.animation_time = 0.0
        self.aim_target = pygame.Vector2(self.rect.centerx + 1, self.rect.centery)
        self.shot_animation_time = 0.0

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

        if self.shot_animation_time > 0:
            self.shot_animation_time = max(0.0, self.shot_animation_time - dt)

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

        weapon = self._get_weapon_surface()
        if weapon is not None:
            screen.blit(weapon, weapon.get_rect(center=self._get_weapon_anchor()))

    def set_aim_target(self, target_position: tuple[int, int]) -> None:
        """Atualiza a mira para alinhar personagem e arma ao cursor."""
        self.aim_target = pygame.Vector2(target_position)

    def use_shot(self, target_position: tuple[int, int]) -> Projectile | None:
        """Dispara um projetil na direcao do cursor, se o cooldown permitir."""
        if not self.shot.is_ready():
            return None

        self.set_aim_target(target_position)

        self.shot.activate()
        self.shot_animation_time = self.WEAPON_FRAME_COUNT / self.WEAPON_ANIMATION_FPS
        spawn_x, spawn_y = self._get_weapon_muzzle()
        projectile_width, projectile_height = self.DART_RENDER_SIZE
        return Projectile(
            spawn_x - (projectile_width // 2),
            spawn_y - (projectile_height // 2),
            target_position[0],
            target_position[1],
            damage=self.shot.damage,
            size=self.DART_RENDER_SIZE,
            custom_surface=self._get_dart_surface(),
        )

    def gain_aura(self, amount: int) -> None:
        """Acumula aura ate o limite maximo."""
        gained_amount = max(0, amount)
        self.aura = min(self.max_aura, self.aura + gained_amount)
        self.total_aura_collected += gained_amount

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

    def _get_weapon_surface(self) -> pygame.Surface | None:
        """Retorna a besta rotacionada na direcao do cursor."""
        frames = self._get_weapon_frames()
        if not frames:
            return None

        if self.shot_animation_time > 0:
            elapsed = (self.WEAPON_FRAME_COUNT / self.WEAPON_ANIMATION_FPS) - self.shot_animation_time
            frame_index = min(len(frames) - 1, int(elapsed * self.WEAPON_ANIMATION_FPS))
        else:
            frame_index = 0

        weapon = frames[frame_index]
        aim_direction = self._get_aim_direction()
        angle = math.degrees(math.atan2(-aim_direction.y, aim_direction.x))
        if self.facing < 0:
            weapon = pygame.transform.flip(weapon, True, False)
            angle -= 180
        weapon = pygame.transform.rotate(weapon, angle)

        if self.invulnerability_timer > 0:
            weapon = weapon.copy()
            weapon.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_ADD)

        return weapon

    def _get_weapon_anchor(self) -> tuple[int, int]:
        """Posiciona a besta proxima da mao frontal do cavaleiro."""
        aim_direction = self._get_aim_direction()
        side_offset = 28 * self.facing
        return (
            int(self.rect.centerx + side_offset + (aim_direction.x * 6)),
            int(self.rect.centery - 12 + (aim_direction.y * 8)),
        )

    def _get_weapon_muzzle(self) -> tuple[int, int]:
        """Usa a ponta da besta como origem visual do disparo."""
        anchor_x, anchor_y = self._get_weapon_anchor()
        aim_direction = self._get_aim_direction()
        return (
            int(anchor_x + (aim_direction.x * 26)),
            int(anchor_y + (aim_direction.y * 12)),
        )

    def _get_aim_direction(self) -> pygame.Vector2:
        """Normaliza a direcao da mira para reaproveitar no desenho e disparo."""
        direction = self.aim_target - pygame.Vector2(self.rect.centerx, self.rect.centery - 10)
        if direction.length_squared() == 0:
            return pygame.Vector2(float(self.facing), 0.0)
        return direction.normalize()

    @classmethod
    def _get_dart_surface(cls) -> pygame.Surface:
        """Cria um dardo reto em pixel art para o tiro da besta."""
        if cls._dart_surface is not None:
            return cls._dart_surface

        dart = pygame.Surface((18, 6), pygame.SRCALPHA)

        dart.set_at((16, 2), (225, 230, 235))
        dart.set_at((17, 2), (245, 248, 250))
        dart.set_at((15, 1), (205, 210, 215))
        dart.set_at((15, 3), (205, 210, 215))

        for x in range(3, 16):
            dart.set_at((x, 2), (132, 92, 58))
        for x in range(4, 14):
            dart.set_at((x, 1), (168, 124, 82))
        for x in range(4, 14):
            dart.set_at((x, 3), (96, 64, 40))

        dart.set_at((0, 1), (180, 40, 40))
        dart.set_at((1, 2), (210, 72, 72))
        dart.set_at((0, 3), (180, 40, 40))
        dart.set_at((2, 1), (130, 24, 24))
        dart.set_at((2, 3), (130, 24, 24))

        cls._dart_surface = pygame.transform.scale(dart, cls.DART_RENDER_SIZE)
        return cls._dart_surface

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

    @classmethod
    def _get_weapon_frames(cls) -> list[pygame.Surface]:
        """Carrega os frames da besta uma unica vez."""
        if cls._weapon_frames is not None:
            return cls._weapon_frames

        if not cls.WEAPON_SHEET_PATH.exists():
            cls._weapon_frames = []
            return cls._weapon_frames

        sheet = pygame.image.load(str(cls.WEAPON_SHEET_PATH)).convert_alpha()
        frames: list[pygame.Surface] = []

        for index in range(cls.WEAPON_FRAME_COUNT):
            frame = pygame.Surface((cls.WEAPON_CELL_SIZE, cls.WEAPON_CELL_SIZE), pygame.SRCALPHA)
            area = pygame.Rect(
                index * cls.WEAPON_CELL_SIZE,
                0,
                cls.WEAPON_CELL_SIZE,
                cls.WEAPON_CELL_SIZE,
            )
            frame.blit(sheet, (0, 0), area)
            frames.append(pygame.transform.scale(frame, cls.WEAPON_RENDER_SIZE))

        cls._weapon_frames = frames
        return cls._weapon_frames
