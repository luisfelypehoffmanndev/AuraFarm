"""Abstracao base para entidades com posicao, vida e ciclo de simulacao."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pygame


class Entity(ABC):
    """Abstracao compartilhada entre player, boss e inimigos auxiliares.

    A classe nao conhece regras de gameplay especificas. Ela apenas oferece a
    estrutura minima comum: hitbox retangular, pontos de vida e contratos de
    update/draw para as subclasses.
    """

    def __init__(self, x: float, y: float, width: int, height: int, max_hp: int) -> None:
        """Inicializa rect e reservas basicas de vida da entidade."""
        self.rect = pygame.Rect(x, y, width, height)
        self.max_hp = max_hp
        self.hp = max_hp

    @abstractmethod
    def update(self, dt: float, *args) -> None:
        """Atualiza estado interno da entidade a cada frame."""
        pass

    @abstractmethod
    def draw(self, screen: pygame.Surface) -> None:
        """Desenha a entidade na tela."""
        pass

    def take_damage(self, amount: int) -> int:
        """Reduz vida e retorna o dano aplicado."""
        damage_applied = min(self.hp, amount)
        self.hp = max(0, self.hp - amount)
        return damage_applied

    def is_alive(self) -> bool:
        """Indica se a entidade ainda possui vida."""
        return self.hp > 0
