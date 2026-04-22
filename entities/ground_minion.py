"""Capanga terrestre que cruza a arena em alta velocidade."""

from __future__ import annotations

import random

import pygame

from entities.entity import Entity
from utils.constants import GROUND_MINION_COLOR, GROUND_MINION_SPEED, GROUND_Y, WIDTH


class GroundMinion(Entity):
    """Inimigo simples de contato, com 1 de HP e movimento reto no chao."""

    def __init__(self, from_left: bool, phase: int) -> None:
        width = 34
        height = 46
        x = -width if from_left else WIDTH + width
        y = GROUND_Y - height
        super().__init__(x, y, width, height, max_hp=1)
        self.direction = 1 if from_left else -1
        self.speed = GROUND_MINION_SPEED + min(phase - 1, 6) * 18 + random.uniform(-20, 20)
        self.contact_damage = 8 + min(phase - 1, 4)

    def update(self, dt: float, *args) -> None:
        """Move o minion rapidamente de um lado ao outro da tela."""
        self.rect.x += int(self.direction * self.speed * dt)

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha o corpo do minion e um olho simples."""
        pygame.draw.rect(screen, GROUND_MINION_COLOR, self.rect, border_radius=6)
        eye_x = self.rect.centerx + (6 if self.direction > 0 else -6)
        pygame.draw.circle(screen, (255, 240, 220), (eye_x, self.rect.y + 14), 4)

    def is_offscreen(self) -> bool:
        """Indica quando o minion ja atravessou toda a arena."""
        return self.rect.right < -80 or self.rect.left > WIDTH + 80
