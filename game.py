"""Loop principal e orquestracao dos sistemas de gameplay do Aura Farming.

Este modulo funciona como coordenador da partida. Ele concentra:
- inicializacao do Pygame e da janela;
- maquina de estados da run;
- listas de entidades temporarias;
- regras de spawn, colisao e progressao;
- ordem de update e draw de cada frame.
"""

from pathlib import Path

import pygame

from entities.aerial_minion import AerialMinion
from entities.aura_drop import AuraDrop
from entities.boss import Boss
from entities.ground_minion import GroundMinion
from entities.player import Player
from entities.projectile import Projectile
from entities.ult_strike import UltStrike
from systems.combat import CombatSystem
from systems.spawn import SpawnSystem
from ui.hud import Hud
from utils.constants import (
    BACKGROUND_COLOR,
    FPS,
    GROUND_Y,
    HEIGHT,
    TITLE,
    WIDTH,
)


class Game:
    """Coordena o estado global da partida e o ciclo de simulacao."""

    BACKGROUND_PATH = Path(__file__).resolve().parent / "assets" / "background.png"

    def __init__(self) -> None:
        """Inicializa o runtime da aplicacao e prepara uma nova run.

        A instancia de ``Game`` existe enquanto a janela estiver aberta. O
        conteudo jogavel em si e reconstruido por ``reset_run()`` quando uma
        nova partida comeca.
        """
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.hud = Hud()
        self.combat_system = CombatSystem()
        self.spawn_system = SpawnSystem()
        self.background = self.load_background()
        self.upgrade_options = [
            ("1", "Aumentar dano do tiro", "+4 de dano por disparo"),
            ("2", "Reduzir cooldown do tiro", "-0.05s entre disparos"),
            ("3", "Fortalecer escudo", "+0.4s de duracao"),
        ]
        self.upgrade_map = {0: "damage", 1: "cooldown", 2: "shield"}
        self.reset_run()

    def reset_run(self) -> None:
        """Reinicia a partida mantendo janela, HUD e assets ja carregados.

        Este metodo reconstrói apenas o estado da run atual. A janela, o clock
        e os objetos de infraestrutura permanecem vivos para que o restart seja
        rapido e previsivel.
        """
        self.state = "running"
        self.player = Player(120, GROUND_Y - 80)
        # O boss fica no centro para reforcar que ele e o foco da arena.
        self.boss = Boss((WIDTH // 2) - 45, 110)
        self.projectiles: list[Projectile] = []
        self.enemy_projectiles: list[Projectile] = []
        self.aura_drops: list[AuraDrop] = []
        self.ult_strikes: list[UltStrike] = []
        self.minions: list[AerialMinion] = []
        self.ground_minions: list[GroundMinion] = []
        self.survival_time = 0.0
        self.scale_timer = 0.0
        self.ground_minion_spawn_timer = 9.0

    def load_background(self) -> pygame.Surface | None:
        """Carrega o fundo da arena quando houver um asset configurado."""
        if not self.BACKGROUND_PATH.exists():
            return None

        background = pygame.image.load(str(self.BACKGROUND_PATH)).convert()
        return pygame.transform.scale(background, (WIDTH, HEIGHT))

    def run(self) -> None:
        """Executa o loop principal enquanto a aplicacao estiver ativa."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            self.handle_events()

            if self.state == "running":
                self.update(dt)

            self.draw(dt)

        pygame.quit()

    def handle_events(self) -> None:
        """Centraliza leitura de input para gameplay, upgrade e game over.

        O tratamento por estado evita que o mesmo input tenha significados
        conflitantes em momentos diferentes da partida.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "running":
                # Botao esquerdo dispara; botao direito ativa o recurso
                # defensivo sem interromper o movimento.
                if event.button == 1:
                    self.spawn_player_projectile(event.pos)

                if event.button == 3:
                    self.player.use_shield()

            if event.type == pygame.KEYDOWN and self.state == "running":
                # O dash fica num atalho separado para nao competir com o pulo.
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.player.use_dash()

            if event.type == pygame.KEYDOWN and self.state == "upgrade":
                if event.key == pygame.K_1:
                    self.apply_upgrade_choice(0)
                elif event.key == pygame.K_2:
                    self.apply_upgrade_choice(1)
                elif event.key == pygame.K_3:
                    self.apply_upgrade_choice(2)

            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "upgrade":
                if event.button == 1:
                    selected_upgrade = self.hud.get_upgrade_at_position(event.pos, len(self.upgrade_options))
                    self.apply_upgrade_choice(selected_upgrade)

            if event.type == pygame.KEYDOWN and self.state == "game_over":
                if event.key == pygame.K_r:
                    self.reset_run()

    def update(self, dt: float) -> None:
        """Atualiza entidades, timers globais e transicoes da partida."""
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)
        self.boss.update(dt, self.player)
        self.update_combat(dt)
        self.update_spawns(dt)

        self.survival_time += dt
        self.scale_timer += dt

        if self.player.aura_ready():
            self.state = "upgrade"

        # O escalonamento temporal complementa a progressao por fase do boss.
        if self.scale_timer >= 12:
            self.boss.scale_up()
            self.scale_timer = 0.0

        if self.player.hp <= 0:
            self.state = "game_over"

    def update_combat(self, dt: float) -> None:
        """Atualiza os sistemas ligados a dano, projeteis e ULTs."""
        self.projectiles, self.minions, self.ground_minions = self.combat_system.update_player_projectiles(
            self.projectiles,
            self.boss,
            self.minions,
            self.ground_minions,
            self.aura_drops,
            dt,
        )
        self.aura_drops = self.combat_system.update_aura_drops(self.player, self.aura_drops, dt)
        self.enemy_projectiles = self.combat_system.update_enemy_projectiles(
            self.player,
            self.boss,
            self.minions,
            self.enemy_projectiles,
            dt,
        )
        self.ult_strikes = self.combat_system.update_boss_ults(
            self.player,
            self.boss,
            self.ult_strikes,
            dt,
        )

    def update_spawns(self, dt: float) -> None:
        """Atualiza os sistemas ligados a invocacao e manutencao de minions."""
        self.spawn_system.update_aerial_minions(self.boss, self.minions, dt)
        self.ground_minions, self.ground_minion_spawn_timer = self.spawn_system.update_ground_minions(
            self.boss,
            self.player,
            self.ground_minions,
            self.ground_minion_spawn_timer,
            self.survival_time,
            dt,
        )

    def spawn_player_projectile(self, target_position: tuple[int, int]) -> None:
        """Cria e registra um tiro do player quando o cooldown permite."""
        self.combat_system.spawn_player_projectile(self.player, self.projectiles, target_position)

    def apply_upgrade_choice(self, selected_upgrade: int | None) -> None:
        """Aplica o upgrade escolhido por indice e fecha o menu."""
        if selected_upgrade not in self.upgrade_map:
            return

        self.player.apply_upgrade(self.upgrade_map[selected_upgrade])
        self.state = "running"

    def draw(self, dt: float) -> None:
        """Desenha cena, inimigos, efeitos e HUD na ordem correta.

        A ordem de desenho importa para manter a leitura visual da arena:
        primeiro fundo, depois entidades e efeitos de combate, e por fim a HUD.
        """
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(BACKGROUND_COLOR)

        self.player.draw(self.screen)
        self.boss.draw(self.screen)
        self.boss.draw_telegraph(self.screen, self.player)

        for projectile in self.projectiles:
            projectile.draw(self.screen)

        for projectile in self.enemy_projectiles:
            projectile.draw(self.screen)

        for drop in self.aura_drops:
            drop.draw(self.screen)

        for strike in self.ult_strikes:
            strike.draw(self.screen)

        for minion in self.minions:
            minion.draw(self.screen)

        for minion in self.ground_minions:
            minion.draw(self.screen)

        self.hud.draw(self.screen, self.player, self.boss, self.survival_time, self.state, self.upgrade_options, dt)
        pygame.display.flip()
