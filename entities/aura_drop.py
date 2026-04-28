"""Coletavel de aura gerado quando o boss recebe dano."""

from __future__ import annotations

import pygame

from utils.constants import AURA_DROP_COLOR, AURA_DROP_GRAVITY, AURA_DROP_LIFETIME, GROUND_Y


class AuraDrop:
    """Orb de aura que cai no chao, pode ser coletado e expira com o tempo."""

    def __init__(self, x: int, y: int, value: int) -> None:
        """Inicializa o drop com impulso inicial para cima e tempo de vida."""
        self.rect = pygame.Rect(x - 10, y - 10, 20, 20)
        self.position = pygame.Vector2(self.rect.x, self.rect.y)
        self.velocity = pygame.Vector2(0, -180)
        self.value = value
        self.time_left = AURA_DROP_LIFETIME

    def update(self, dt: float) -> None:
        """Aplica gravidade e reduz o tempo de vida do coletavel."""
        self.time_left = max(0.0, self.time_left - dt)

        self.velocity.y += AURA_DROP_GRAVITY * dt
        self.position += self.velocity * dt
        self.rect.x = int(self.position.x)
        self.rect.y = int(self.position.y)

        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.position.y = self.rect.y
            self.velocity.y = 0

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha o orb com brilho e fade perto do fim da vida util."""
        alpha = 255 if self.time_left > 1.0 else int(255 * max(0.25, self.time_left))
        glow = pygame.Surface((34, 34), pygame.SRCALPHA)
        pygame.draw.circle(glow, (AURA_DROP_COLOR[0], AURA_DROP_COLOR[1], AURA_DROP_COLOR[2], alpha // 3), (17, 17), 16)
        screen.blit(glow, glow.get_rect(center=self.rect.center))

        orb = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(orb, (AURA_DROP_COLOR[0], AURA_DROP_COLOR[1], AURA_DROP_COLOR[2], alpha), (10, 10), 8)
        screen.blit(orb, orb.get_rect(center=self.rect.center))

    def is_expired(self) -> bool:
        """Informa quando o orb deve ser removido."""
        return self.time_left <= 0.0
