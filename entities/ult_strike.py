"""Ataque de coluna vertical usado nas ULTs do boss."""

from __future__ import annotations

from pathlib import Path

import pygame

from utils.constants import BOSS_ULT_ACTIVE, BOSS_ULT_COLOR, BOSS_ULT_TELEGRAPH, HEIGHT


class UltStrike:
    """Coluna com telegraph e janela curta de dano."""

    LIGHTNING_SHEET_PATH = Path(__file__).resolve().parent.parent / "assets" / "effects" / "raio_spritesheet.png"
    LIGHTNING_FRAME_COUNT = 8
    _lightning_frames: list[pygame.Surface] | None = None

    def __init__(self, center_x: int, width: int, damage: int) -> None:
        """Inicializa uma coluna vertical cobrindo toda a altura da arena."""
        self.rect = pygame.Rect(center_x - width // 2, 0, width, HEIGHT)
        self.damage = damage
        self.telegraph_timer = BOSS_ULT_TELEGRAPH
        self.active_timer = BOSS_ULT_ACTIVE
        self.has_hit = False
        self.animation_time = 0.0

    def update(self, dt: float) -> None:
        """Alterna entre fase de aviso e fase ativa."""
        if self.telegraph_timer > 0:
            self.telegraph_timer = max(0.0, self.telegraph_timer - dt)
        else:
            self.active_timer = max(0.0, self.active_timer - dt)
            self.animation_time += dt

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha a coluna em modo aviso ou impacto.

        A renderizacao usa um overlay separado para que o efeito atravesse a
        arena inteira sem precisar interferir na ordem de draw das entidades.
        """
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        if self.telegraph_timer > 0:
            alpha = int(70 + (1.0 - self.telegraph_timer / BOSS_ULT_TELEGRAPH) * 110)
            pygame.draw.rect(overlay, (255, 120, 120, alpha), self.rect, 3)
        else:
            pygame.draw.rect(overlay, (*BOSS_ULT_COLOR, 110), self.rect)
            frames = self._get_lightning_frames()
            if frames:
                frame_index = int(self.animation_time * 16.0) % len(frames)
                lightning = pygame.transform.scale(frames[frame_index], self.rect.size)
                overlay.blit(lightning, self.rect.topleft)
            else:
                pygame.draw.rect(overlay, (255, 255, 255, 220), self.rect.inflate(-self.rect.width // 2, 0))

        screen.blit(overlay, (0, 0))

    def can_hit(self) -> bool:
        """Permite dano apenas uma vez durante a fase ativa."""
        return self.telegraph_timer <= 0 and self.active_timer > 0 and not self.has_hit

    def is_finished(self) -> bool:
        """Indica quando a coluna ja terminou por completo."""
        return self.telegraph_timer <= 0 and self.active_timer <= 0

    @classmethod
    def _get_lightning_frames(cls) -> list[pygame.Surface]:
        """Carrega os frames do raio uma vez e reutiliza nas ULTs seguintes."""
        if cls._lightning_frames is not None:
            return cls._lightning_frames

        if not cls.LIGHTNING_SHEET_PATH.exists():
            cls._lightning_frames = []
            return cls._lightning_frames

        sheet = pygame.image.load(str(cls.LIGHTNING_SHEET_PATH)).convert_alpha()
        frame_width = sheet.get_width() // cls.LIGHTNING_FRAME_COUNT
        frame_height = sheet.get_height()
        frames: list[pygame.Surface] = []

        for index in range(cls.LIGHTNING_FRAME_COUNT):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), pygame.Rect(index * frame_width, 0, frame_width, frame_height))
            frames.append(frame)

        cls._lightning_frames = frames
        return cls._lightning_frames
