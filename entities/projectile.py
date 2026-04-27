"""Projetil generico reutilizado por player, boss e capangas."""

from __future__ import annotations

import math
from pathlib import Path

import pygame

from utils.constants import HEIGHT, PROJECTILE_COLOR, PROJECTILE_SPEED, WIDTH


class Projectile:
    """Projetil retilineo que usa um alvo inicial para definir a direcao.

    A classe e flexivel o bastante para representar desde um retangulo simples
    ate um projetil animado com spritesheet e rotacao.
    """

    _animation_cache: dict[tuple[str, str, str | None, int, tuple[int, int] | None], list[pygame.Surface]] = {}

    def __init__(
        self,
        x: int,
        y: int,
        target_x: int,
        target_y: int,
        damage: int = 10,
        speed: float = PROJECTILE_SPEED,
        color: tuple[int, int, int] = PROJECTILE_COLOR,
        size: tuple[int, int] = (18, 8),
        sprite_folder: str | None = None,
        sprite_prefix: str = "fly",
        sprite_sheet_path: str | None = None,
        sprite_frame_count: int = 1,
        sprite_size: tuple[int, int] | None = None,
        animation_fps: float = 12.0,
    ) -> None:
        """Inicializa o projetil e calcula seu vetor de movimento."""
        self.rect = pygame.Rect(x, y, size[0], size[1])
        self.damage = damage
        self.position = pygame.Vector2(x, y)
        self.color = color
        self.animation_time = 0.0
        self.animation_fps = animation_fps
        self.frames = self.load_frames(
            sprite_folder,
            sprite_prefix,
            sprite_sheet_path,
            sprite_frame_count,
            sprite_size,
        )

        direction = pygame.Vector2(target_x - x, target_y - y)
        if direction.length_squared() == 0:
            # Evita normalizacao de vetor nulo se o tiro nascer exatamente no
            # ponto-alvo.
            direction = pygame.Vector2(1, 0)

        self.velocity = direction.normalize() * speed

    @classmethod
    def load_frames(
        cls,
        sprite_folder: str | None,
        sprite_prefix: str,
        sprite_sheet_path: str | None,
        sprite_frame_count: int,
        sprite_size: tuple[int, int] | None,
    ) -> list[pygame.Surface]:
        """Carrega frames animados uma vez e reutiliza nos projeteis seguintes."""
        if sprite_folder is None and sprite_sheet_path is None:
            return []

        cache_key = (sprite_folder or "", sprite_prefix, sprite_sheet_path, sprite_frame_count, sprite_size)
        if cache_key in cls._animation_cache:
            return cls._animation_cache[cache_key]

        frames: list[pygame.Surface] = []

        if sprite_sheet_path is not None:
            # Caminho usado quando o asset ja foi consolidado em uma spritesheet
            # horizontal unica.
            sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
            frame_width = sheet.get_width() // max(1, sprite_frame_count)
            frame_height = sheet.get_height()

            for index in range(sprite_frame_count):
                raw_frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
                raw_frame.blit(sheet, (0, 0), pygame.Rect(index * frame_width, 0, frame_width, frame_height))
                frame = cls._normalize_frame(raw_frame)
                if sprite_size is not None:
                    frame = pygame.transform.scale(frame, sprite_size)
                frames.append(frame)
        else:
            # Fallback para sequencias de PNGs individuais. Se houver variante
            # 4x, ela tem prioridade por oferecer mais definicao.
            folder = Path(sprite_folder)
            frame_paths = sorted(folder.glob(f"{sprite_prefix}_*_4x.png"))
            if not frame_paths:
                frame_paths = sorted(folder.glob(f"{sprite_prefix}_*.png"))

            for frame_path in frame_paths:
                frame = cls._normalize_frame(pygame.image.load(str(frame_path)).convert_alpha())
                if sprite_size is not None:
                    frame = pygame.transform.scale(frame, sprite_size)
                frames.append(frame)

        cls._animation_cache[cache_key] = frames
        return frames

    @staticmethod
    def _normalize_frame(frame: pygame.Surface) -> pygame.Surface:
        """Centraliza o frame em uma area quadrada para evitar sprite achatado ao rotacionar."""
        side = max(frame.get_width(), frame.get_height())
        normalized = pygame.Surface((side, side), pygame.SRCALPHA)
        normalized.blit(frame, frame.get_rect(center=normalized.get_rect().center))
        return normalized

    def update(self, dt: float) -> None:
        """Avanca o projetil de acordo com sua velocidade."""
        self.position += self.velocity * dt
        self.rect.x = int(self.position.x)
        self.rect.y = int(self.position.y)
        self.animation_time += dt

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha o projetil orientado na direcao do movimento."""
        angle = math.degrees(math.atan2(-self.velocity.y, self.velocity.x))

        if self.frames:
            frame_index = int(self.animation_time * self.animation_fps) % len(self.frames)
            surface = self.frames[frame_index]
        else:
            surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            surface.fill(self.color)

        rotated = pygame.transform.rotate(surface, angle)
        screen.blit(rotated, rotated.get_rect(center=self.rect.center))

    def is_visible(self) -> bool:
        """Mantem apenas projeteis dentro da area util da tela."""
        return -self.rect.width <= self.rect.x <= WIDTH and -self.rect.height <= self.rect.y <= HEIGHT
