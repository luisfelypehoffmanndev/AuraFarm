"""Capanga voador fraco, usado como pressao secundaria no combate."""

from __future__ import annotations

import math
import random

import pygame

from entities.entity import Entity
from entities.projectile import Projectile
from utils.constants import (
    AERIAL_MINION_COLOR,
    AERIAL_MINION_PROJECTILE_COLOR,
    MINION_PROJECTILE_SPEED,
    WIDTH,
)


class AerialMinion(Entity):
    """Inimigo aereo com 1 de HP e disparos fracos em intervalos curtos."""

    def __init__(self, x: float, y: float, phase: int) -> None:
        super().__init__(x, y, 42, 42, max_hp=1)
        self.anchor_x = x
        self.anchor_y = y
        self.time = random.uniform(0.0, 3.14)
        self.move_speed = 1.1 + phase * 0.05
        self.move_range = 48 + phase * 3
        self.attack_cooldown = max(1.4, 2.3 - phase * 0.08)
        self.attack_timer = random.uniform(0.2, self.attack_cooldown)
        self.projectile_damage = 4 + min(phase - 1, 4)

    def update(self, dt: float, *args) -> None:
        """Oscila no ar e prepara o proximo disparo."""
        self.time += dt
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.rect.x = int(self.anchor_x + math.sin(self.time * self.move_speed) * self.move_range)
        self.rect.y = int(self.anchor_y + math.cos(self.time * 1.7) * 18)
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha o corpo do minion e um ponto de destaque no centro."""
        pygame.draw.ellipse(screen, AERIAL_MINION_COLOR, self.rect)
        pygame.draw.circle(screen, (255, 240, 210), self.rect.center, 6)

    def try_attack(self, target: Entity) -> Projectile | None:
        """Dispara um projetil fraco na direcao do player."""
        if self.attack_timer > 0:
            return None

        self.attack_timer = self.attack_cooldown
        return Projectile(
            self.rect.centerx,
            self.rect.centery,
            target.rect.centerx,
            target.rect.centery,
            damage=self.projectile_damage,
            speed=MINION_PROJECTILE_SPEED,
            color=AERIAL_MINION_PROJECTILE_COLOR,
            size=(12, 12),
        )
