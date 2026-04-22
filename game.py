"""Loop principal e orquestracao de todos os sistemas do jogo."""

import pygame

from entities.aerial_minion import AerialMinion
from entities.aura_drop import AuraDrop
from entities.boss import Boss
from entities.ground_minion import GroundMinion
from entities.player import Player
from entities.projectile import Projectile
from entities.ult_strike import UltStrike
from ui.hud import Hud
from utils.constants import (
    BACKGROUND_COLOR,
    FPS,
    GROUND_MINION_MAX_ALIVE,
    GROUND_MINION_SPAWN_COOLDOWN,
    GROUND_Y,
    HEIGHT,
    TITLE,
    WIDTH,
)


class Game:
    """Coordena estado, entidades, combate e transicoes de tela."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.hud = Hud()
        self.upgrade_options = [
            ("1", "Aumentar dano do tiro", "+4 de dano por disparo"),
            ("2", "Reduzir cooldown do tiro", "-0.05s entre disparos"),
            ("3", "Fortalecer escudo", "+0.4s de duracao"),
        ]
        self.upgrade_map = {0: "damage", 1: "cooldown", 2: "shield"}
        self.reset_run()

    def reset_run(self) -> None:
        """Reinicia a partida mantendo a janela e os recursos carregados."""
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
        self.ground_minion_spawn_timer = 3.5

    def run(self) -> None:
        """Executa o loop principal enquanto a janela estiver aberta."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            self.handle_events()

            if self.state == "running":
                self.update(dt)

            self.draw()

        pygame.quit()

    def handle_events(self) -> None:
        """Centraliza leitura de input para gameplay, upgrade e game over."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "running":
                if event.button == 1:
                    self.spawn_player_projectile(event.pos)

                if event.button == 3:
                    self.player.use_shield()

            if event.type == pygame.KEYDOWN and self.state == "running":
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
        """Atualiza entidades e sistemas ativos da partida."""
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)
        self.boss.update(dt, self.player)
        self.update_projectiles(dt)
        self.update_aura_drops(dt)
        self.update_enemy_attacks(dt)
        self.update_boss_ults(dt)
        self.update_minions(dt)
        self.update_ground_minions(dt)

        self.survival_time += dt
        self.scale_timer += dt

        if self.player.aura_ready():
            self.state = "upgrade"

        # O boss fica mais perigoso em passos simples para manter o escopo sob controle.
        if self.scale_timer >= 8:
            self.boss.scale_up()
            self.scale_timer = 0.0

        if self.player.hp <= 0:
            self.state = "game_over"

    def update_projectiles(self, dt: float) -> None:
        """Atualiza tiros do player e resolve colisao com inimigos."""
        alive_projectiles: list[Projectile] = []

        for projectile in self.projectiles:
            projectile.update(dt)

            if self.resolve_player_projectile_hit(projectile):
                continue

            if projectile.is_visible():
                alive_projectiles.append(projectile)

        self.projectiles = alive_projectiles
        self.minions = [minion for minion in self.minions if minion.is_alive()]
        self.ground_minions = [minion for minion in self.ground_minions if minion.is_alive()]

    def update_aura_drops(self, dt: float) -> None:
        """Atualiza orbs de aura e coleta quando o player encosta."""
        alive_drops: list[AuraDrop] = []

        for drop in self.aura_drops:
            drop.update(dt)

            if drop.rect.colliderect(self.player.rect):
                self.player.gain_aura(drop.value)
                continue

            if not drop.is_expired():
                alive_drops.append(drop)

        self.aura_drops = alive_drops

    def update_enemy_attacks(self, dt: float) -> None:
        """Atualiza tiros do boss e dos capangas voadores."""
        self.add_enemy_projectile(self.boss.try_attack(self.player))

        for minion in self.minions:
            self.add_enemy_projectile(minion.try_attack(self.player))

        alive_projectiles: list[Projectile] = []

        for projectile in self.enemy_projectiles:
            projectile.update(dt)

            if projectile.rect.colliderect(self.player.rect):
                self.player.take_damage(projectile.damage)
                continue

            if projectile.is_visible():
                alive_projectiles.append(projectile)

        self.enemy_projectiles = alive_projectiles

    def update_minions(self, dt: float) -> None:
        """Controla spawn e movimento dos capangas voadores."""
        self.spawn_aerial_minions()

        for minion in self.minions:
            minion.update(dt)

    def update_boss_ults(self, dt: float) -> None:
        """Atualiza o ciclo de ULTs do boss e aplica dano das colunas."""
        new_strikes = self.boss.try_ult(self.player)
        if new_strikes:
            self.ult_strikes.extend(new_strikes)

        active_strikes: list[UltStrike] = []

        for strike in self.ult_strikes:
            strike.update(dt)

            if strike.can_hit() and strike.rect.colliderect(self.player.rect):
                self.player.take_damage(strike.damage)
                strike.has_hit = True

            if not strike.is_finished():
                active_strikes.append(strike)

        self.ult_strikes = active_strikes

    def update_ground_minions(self, dt: float) -> None:
        """Controla spawn e travessia dos capangas terrestres."""
        self.ground_minion_spawn_timer = max(0.0, self.ground_minion_spawn_timer - dt)
        max_alive = min(GROUND_MINION_MAX_ALIVE, 1 + self.boss.phase // 3)

        self.spawn_ground_minion_if_needed(max_alive)

        alive_minions: list[GroundMinion] = []
        for minion in self.ground_minions:
            minion.update(dt)

            if minion.rect.colliderect(self.player.rect):
                self.player.take_damage(minion.contact_damage)
                continue

            if not minion.is_offscreen() and minion.is_alive():
                alive_minions.append(minion)

        self.ground_minions = alive_minions

    def spawn_player_projectile(self, target_position: tuple[int, int]) -> None:
        """Cria e registra um tiro do player quando o cooldown permite."""
        projectile = self.player.use_shot(target_position)
        if projectile is not None:
            self.projectiles.append(projectile)

    def apply_upgrade_choice(self, selected_upgrade: int | None) -> None:
        """Aplica o upgrade escolhido por indice e fecha o menu."""
        if selected_upgrade not in self.upgrade_map:
            return

        self.player.apply_upgrade(self.upgrade_map[selected_upgrade])
        self.state = "running"

    def resolve_player_projectile_hit(self, projectile: Projectile) -> bool:
        """Resolve o primeiro alvo atingido por um tiro do player."""
        if projectile.rect.colliderect(self.boss.rect):
            damage_dealt = self.boss.take_damage(projectile.damage)
            self.aura_drops.append(AuraDrop(self.boss.rect.centerx, self.boss.rect.bottom, damage_dealt))
            return True

        for enemy_group in (self.minions, self.ground_minions):
            for enemy in enemy_group:
                if projectile.rect.colliderect(enemy.rect):
                    enemy.take_damage(projectile.damage)
                    return True

        return False

    def add_enemy_projectile(self, projectile: Projectile | None) -> None:
        """Adiciona um projetil inimigo apenas quando ele existir."""
        if projectile is not None:
            self.enemy_projectiles.append(projectile)

    def spawn_aerial_minions(self) -> None:
        """Cria novos capangas voadores quando o boss pode invocar."""
        max_alive = self.boss.get_max_aerial_minions()
        if not self.boss.should_spawn_minion(len(self.minions)):
            return

        for x, y in self.boss.get_minion_spawn_positions():
            if len(self.minions) >= max_alive:
                break
            self.minions.append(AerialMinion(x, y, self.boss.phase))

    def spawn_ground_minion_if_needed(self, max_alive: int) -> None:
        """Cria um capanga terrestre se houver espaco e cooldown livre."""
        if self.ground_minion_spawn_timer > 0 or len(self.ground_minions) >= max_alive:
            return

        from_left = (int(self.survival_time) // 2) % 2 == 0
        self.ground_minions.append(GroundMinion(from_left=from_left, phase=self.boss.phase))
        self.ground_minion_spawn_timer = max(3.4, GROUND_MINION_SPAWN_COOLDOWN - self.boss.phase * 0.15)

    def draw(self) -> None:
        """Desenha cena, inimigos, efeitos e HUD na ordem correta."""
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

        self.hud.draw(self.screen, self.player, self.boss, self.survival_time, self.state, self.upgrade_options)
        pygame.display.flip()
