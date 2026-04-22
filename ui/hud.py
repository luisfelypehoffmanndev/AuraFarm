"""HUD e overlays de interface do jogo."""

import pygame

from entities.boss import Boss
from entities.player import Player
from utils.constants import HEIGHT, HUD_TEXT_COLOR, RED, WHITE, WIDTH


class Hud:
    """Desenha barras, overlays e interacoes visuais da interface."""

    def __init__(self) -> None:
        self.font = pygame.font.SysFont("consolas", 18)
        self.small_font = pygame.font.SysFont("consolas", 14)

    def draw(
        self,
        screen: pygame.Surface,
        player: Player,
        boss: Boss,
        survival_time: float,
        state: str,
        upgrade_options: list[tuple[str, str, str]],
    ) -> None:
        """Desenha a HUD persistente e os overlays dependentes de estado."""
        self.draw_boss_bar(screen, boss)
        self.draw_status_panel(screen, player, survival_time)

        if state == "upgrade":
            self.draw_upgrade_menu(screen, upgrade_options)

        if state == "game_over":
            self.draw_game_over(screen, survival_time)

    def draw_boss_bar(self, screen: pygame.Surface, boss: Boss) -> None:
        """Barra de vida superior do boss e indicador de recuperacao."""
        panel_width = 360
        panel_height = 34
        panel_x = (WIDTH - panel_width) // 2
        panel_y = 20

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((8, 10, 16, 100))
        screen.blit(panel, (panel_x, panel_y))

        label = self.small_font.render("BOSS", True, WHITE)
        screen.blit(label, (panel_x + 12, panel_y + 9))

        bar_x = panel_x + 58
        bar_y = panel_y + 11
        bar_width = 286
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, 12), 1)
        ratio = boss.hp / boss.max_hp if boss.max_hp else 0
        pygame.draw.rect(screen, RED, (bar_x + 2, bar_y + 2, int((bar_width - 4) * ratio), 8))

        if boss.is_healing():
            text = self.small_font.render(f"RECUPERANDO {boss.heal_pause_timer:0.1f}s", True, (255, 230, 170))
            screen.blit(text, (panel_x + panel_width + 12, panel_y + 9))

    def draw_status_panel(self, screen: pygame.Surface, player: Player, survival_time: float) -> None:
        """Painel inferior com tempo, HP e aura do player."""
        panel_width = 520
        panel_height = 56
        panel_x = 24
        panel_y = HEIGHT - panel_height - 18

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((8, 10, 16, 110))
        screen.blit(panel, (panel_x, panel_y))

        timer_surface = self.font.render(f"Tempo {survival_time:05.1f}s", True, HUD_TEXT_COLOR)
        screen.blit(timer_surface, (panel_x + 16, panel_y + 16))

        self.draw_hp_bar(screen, player, panel_x, panel_y)
        self.draw_aura_bar(screen, player, panel_x, panel_y)

    def draw_hp_bar(self, screen: pygame.Surface, player: Player, panel_x: int, panel_y: int) -> None:
        """Barra de vida do player."""
        bar_x = panel_x + 190
        bar_y = panel_y + 17
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, 118, 12), 1)
        ratio = player.hp / player.max_hp if player.max_hp else 0
        pygame.draw.rect(screen, RED, (bar_x + 2, bar_y + 2, int(114 * ratio), 8))

        label = self.small_font.render("HP", True, WHITE)
        screen.blit(label, (bar_x - 28, bar_y - 2))

    def draw_aura_bar(self, screen: pygame.Surface, player: Player, panel_x: int, panel_y: int) -> None:
        """Barra de aura do player."""
        bar_x = panel_x + 360
        bar_y = panel_y + 17
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, 118, 12), 1)
        ratio = player.aura / player.max_aura if player.max_aura else 0
        pygame.draw.rect(screen, (80, 160, 255), (bar_x + 2, bar_y + 2, int(114 * ratio), 8))

        label = self.small_font.render("AURA", True, WHITE)
        screen.blit(label, (bar_x - 48, bar_y - 2))

    def draw_game_over(self, screen: pygame.Surface, survival_time: float) -> None:
        """Overlay simples de fim de jogo."""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        title = self.font.render("Game Over", True, WHITE)
        subtitle = self.small_font.render(f"Sobreviveu por {survival_time:05.1f}s", True, WHITE)
        hint = self.small_font.render("Pressione R para reiniciar", True, WHITE)

        screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 25)))
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 52)))

    def draw_upgrade_menu(self, screen: pygame.Surface, upgrade_options: list[tuple[str, str, str]]) -> None:
        """Menu de upgrade com hover e suporte a clique."""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))
        mouse_position = pygame.mouse.get_pos()

        title = self.font.render("Aura cheia", True, WHITE)
        subtitle = self.small_font.render("Clique em um upgrade ou use 1, 2, 3", True, WHITE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 116)))
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 88)))

        for index, (key, label, description) in enumerate(upgrade_options):
            card_x, card_y, card_width, card_height = self.get_upgrade_card_rect(index, len(upgrade_options))
            card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
            hovered = card_rect.collidepoint(mouse_position)
            card = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
            card.fill((28, 34, 48, 235) if hovered else (18, 22, 32, 220))
            screen.blit(card, (card_x, card_y))
            pygame.draw.rect(screen, (255, 230, 170) if hovered else WHITE, (card_x, card_y, card_width, card_height), 1)

            key_surface = self.font.render(key, True, WHITE)
            title_surface = self.small_font.render(label, True, WHITE)
            description_surface = self.small_font.render(description, True, (200, 210, 220))

            screen.blit(key_surface, (card_x + 16, card_y + 18))
            screen.blit(title_surface, (card_x + 52, card_y + 16))
            screen.blit(description_surface, (card_x + 52, card_y + 42))

    def get_upgrade_card_rect(self, index: int, total_cards: int) -> tuple[int, int, int, int]:
        """Calcula o retangulo de um card de upgrade pelo indice."""
        card_width = 320
        card_height = 78
        gap = 24
        total_width = card_width * total_cards + gap * (total_cards - 1)
        start_x = (WIDTH - total_width) // 2
        card_y = HEIGHT // 2 - 30
        card_x = start_x + index * (card_width + gap)
        return card_x, card_y, card_width, card_height

    def get_upgrade_at_position(self, position: tuple[int, int], total_cards: int) -> int | None:
        """Retorna qual card foi clicado, se houver um na posicao."""
        mouse_x, mouse_y = position

        for index in range(total_cards):
            card_x, card_y, card_width, card_height = self.get_upgrade_card_rect(index, total_cards)
            rect = pygame.Rect(card_x, card_y, card_width, card_height)
            if rect.collidepoint(mouse_x, mouse_y):
                return index

        return None
