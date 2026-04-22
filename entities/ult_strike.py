"""Ataque de coluna vertical usado nas ULTs do boss."""

from __future__ import annotations

import pygame

from utils.constants import BOSS_ULT_ACTIVE, BOSS_ULT_COLOR, BOSS_ULT_TELEGRAPH, HEIGHT


class UltStrike:
    """Coluna com telegraph e janela curta de dano."""

    def __init__(self, center_x: int, width: int, damage: int) -> None:
        self.rect = pygame.Rect(center_x - width // 2, 0, width, HEIGHT)
        self.damage = damage
        self.telegraph_timer = BOSS_ULT_TELEGRAPH
        self.active_timer = BOSS_ULT_ACTIVE
        self.has_hit = False

    def update(self, dt: float) -> None:
        """Alterna entre fase de aviso e fase ativa."""
        if self.telegraph_timer > 0:
            self.telegraph_timer = max(0.0, self.telegraph_timer - dt)
        else:
            self.active_timer = max(0.0, self.active_timer - dt)

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha a coluna em modo aviso ou impacto."""
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        if self.telegraph_timer > 0:
            alpha = int(70 + (1.0 - self.telegraph_timer / BOSS_ULT_TELEGRAPH) * 110)
            pygame.draw.rect(overlay, (255, 120, 120, alpha), self.rect, 3)
        else:
            pygame.draw.rect(overlay, (*BOSS_ULT_COLOR, 180), self.rect)
            pygame.draw.rect(overlay, (255, 255, 255, 220), self.rect.inflate(-self.rect.width // 2, 0))

        screen.blit(overlay, (0, 0))

    def can_hit(self) -> bool:
        """Permite dano apenas uma vez durante a fase ativa."""
        return self.telegraph_timer <= 0 and self.active_timer > 0 and not self.has_hit

    def is_finished(self) -> bool:
        """Indica quando a coluna ja terminou por completo."""
        return self.telegraph_timer <= 0 and self.active_timer <= 0
