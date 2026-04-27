"""Capanga terrestre que cruza a arena em alta velocidade."""

from __future__ import annotations

from pathlib import Path
import random

import pygame

from entities.entity import Entity
from utils.constants import GROUND_MINION_COLOR, GROUND_MINION_SPEED, GROUND_Y, WIDTH


class GroundMinion(Entity):
    """Inimigo simples de contato, com 1 de HP e movimento reto no chao."""

    SPRITE_SHEET_PATH = Path(__file__).resolve().parent.parent / "assets" / "minions" / "seis_sheet.png"
    SPRITE_FRAME_COUNT = 8
    SPRITE_FRAME_DURATION = 0.1
    SPRITE_DRAW_SIZE = (72, 72)

    def __init__(self, from_left: bool, phase: int) -> None:
        """Inicializa lado de entrada, velocidade e animacao do minion."""
        width = 34
        height = 46
        x = -width if from_left else WIDTH + width
        y = GROUND_Y - height
        super().__init__(x, y, width, height, max_hp=1)
        self.direction = 1 if from_left else -1
        self.speed = GROUND_MINION_SPEED + min(phase - 1, 6) * 18 + random.uniform(-20, 20)
        self.contact_damage = 8 + min(phase - 1, 4)
        self.animation_timer = random.uniform(0.0, self.SPRITE_FRAME_DURATION * self.SPRITE_FRAME_COUNT)
        self.current_frame = random.randrange(self.SPRITE_FRAME_COUNT)
        self.sprite_frames = self._load_sprite_frames()

    def update(self, dt: float, *args) -> None:
        """Move o minion rapidamente de um lado ao outro da tela."""
        self.rect.x += int(self.direction * self.speed * dt)
        self._update_animation(dt)

    def draw(self, screen: pygame.Surface) -> None:
        """Desenha o corpo do minion e um olho simples."""
        if self.sprite_frames:
            frame = self.sprite_frames[self.current_frame]
            if self.direction < 0:
                frame = pygame.transform.flip(frame, True, False)

            sprite_rect = frame.get_rect(midbottom=self.rect.midbottom)
            screen.blit(frame, sprite_rect)
        else:
            pygame.draw.rect(screen, GROUND_MINION_COLOR, self.rect, border_radius=6)
            eye_x = self.rect.centerx + (6 if self.direction > 0 else -6)
            pygame.draw.circle(screen, (255, 240, 220), (eye_x, self.rect.y + 14), 4)

    def is_offscreen(self) -> bool:
        """Indica quando o minion ja atravessou toda a arena."""
        return self.rect.right < -80 or self.rect.left > WIDTH + 80

    def _load_sprite_frames(self) -> list[pygame.Surface]:
        """Carrega e fatia os frames do capanga terrestre."""
        if not self.SPRITE_SHEET_PATH.exists():
            return []

        sheet = pygame.image.load(str(self.SPRITE_SHEET_PATH)).convert_alpha()
        frame_width = sheet.get_width() // self.SPRITE_FRAME_COUNT
        frame_height = sheet.get_height()
        frames: list[pygame.Surface] = []

        for index in range(self.SPRITE_FRAME_COUNT):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), pygame.Rect(index * frame_width, 0, frame_width, frame_height))
            frames.append(pygame.transform.scale(frame, self.SPRITE_DRAW_SIZE))

        return frames

    def _update_animation(self, dt: float) -> None:
        """Avanca a animacao do minion em loop."""
        if not self.sprite_frames:
            return

        self.animation_timer += dt
        while self.animation_timer >= self.SPRITE_FRAME_DURATION:
            self.animation_timer -= self.SPRITE_FRAME_DURATION
            self.current_frame = (self.current_frame + 1) % len(self.sprite_frames)
