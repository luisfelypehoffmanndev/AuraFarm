"""Entidade controlada pelo jogador."""

from __future__ import annotations

import math
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
    """Controla movimento, recursos, skills e dano recebido pelo player."""

    def __init__(self, x: float, y: float) -> None:
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

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        """Aplica movimento, gravidade, cooldowns e timers defensivos."""
        direction = 0

        if keys[pygame.K_a]:
            direction -= 1
        if keys[pygame.K_d]:
            direction += 1

        if direction != 0:
            self.dash.last_direction = int(math.copysign(1, direction))

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

        if self.shield.active_timer > 0:
            self.shield.active_timer = max(0.0, self.shield.active_timer - dt)

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha o player e o efeito visual do escudo quando ativo."""
        if self.shield.active_timer > 0:
            pygame.draw.circle(screen, (120, 180, 255), self.rect.center, 40, 3)

        color = (255, 255, 255) if self.invulnerability_timer > 0 else PLAYER_COLOR
        pygame.draw.rect(screen, color, self.rect)

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
        """Executa um deslocamento curto na ultima direcao horizontal usada."""
        if not self.dash.is_ready():
            return

        self.dash.activate()
        direction = self.dash.last_direction or 1
        self.rect.x += direction * self.dash.distance
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))

    def use_shield(self) -> None:
        """Ativa imunidade temporaria se o shield estiver disponivel."""
        if not self.shield.is_ready():
            return

        self.shield.activate()

    def apply_upgrade(self, kind: str) -> None:
        """Aplica um upgrade simples e reseta a barra de aura."""
        # O upgrade mexe em poucos atributos para manter a regra clara e facil de explicar.
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
