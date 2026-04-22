"""Projetil generico reutilizado por player, boss e capangas."""

from __future__ import annotations

import math
import pygame

from utils.constants import HEIGHT, PROJECTILE_COLOR, PROJECTILE_SPEED, WIDTH


class Projectile:
    """Projetil retilineo que usa um alvo inicial para definir a direcao."""

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
    ) -> None:
        self.rect = pygame.Rect(x, y, size[0], size[1])
        self.damage = damage
        self.position = pygame.Vector2(x, y)
        self.color = color

        direction = pygame.Vector2(target_x - x, target_y - y)
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)

        self.velocity = direction.normalize() * speed

    def update(self, dt: float) -> None:
        """Avanca o projetil de acordo com sua velocidade."""
        self.position += self.velocity * dt
        self.rect.x = int(self.position.x)
        self.rect.y = int(self.position.y)

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha o projetil orientado na direcao do movimento."""
        angle = math.degrees(math.atan2(-self.velocity.y, self.velocity.x))
        surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        surface.fill(self.color)
        rotated = pygame.transform.rotate(surface, angle)
        screen.blit(rotated, rotated.get_rect(center=self.rect.center))

    def is_visible(self) -> bool:
        """Mantem apenas projeteis dentro da area util da tela."""
        return -self.rect.width <= self.rect.x <= WIDTH and -self.rect.height <= self.rect.y <= HEIGHT
