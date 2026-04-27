"""Sistema responsavel por dano, projeteis e ULTs."""

from __future__ import annotations

from entities.aerial_minion import AerialMinion
from entities.aura_drop import AuraDrop
from entities.boss import Boss
from entities.ground_minion import GroundMinion
from entities.player import Player
from entities.projectile import Projectile
from entities.ult_strike import UltStrike


class CombatSystem:
    """Concentra a logica de combate para reduzir o peso de ``Game``.

    O sistema nao guarda estado proprio da run. Ele recebe as colecoes ativas,
    aplica as regras de combate e devolve as listas atualizadas para o
    coordenador principal.
    """

    def spawn_player_projectile(
        self,
        player: Player,
        projectiles: list[Projectile],
        target_position: tuple[int, int],
    ) -> None:
        """Cria e registra um tiro do player quando o cooldown permitir."""
        projectile = player.use_shot(target_position)
        if projectile is not None:
            projectiles.append(projectile)

    def update_player_projectiles(
        self,
        projectiles: list[Projectile],
        boss: Boss,
        minions: list[AerialMinion],
        ground_minions: list[GroundMinion],
        aura_drops: list[AuraDrop],
        dt: float,
    ) -> tuple[list[Projectile], list[AerialMinion], list[GroundMinion]]:
        """Atualiza tiros do player e resolve o primeiro alvo valido de cada um."""
        alive_projectiles: list[Projectile] = []

        for projectile in projectiles:
            projectile.update(dt)

            if self._resolve_player_projectile_hit(projectile, boss, minions, ground_minions, aura_drops):
                continue

            if projectile.is_visible():
                alive_projectiles.append(projectile)

        alive_minions = [minion for minion in minions if minion.is_alive()]
        alive_ground_minions = [minion for minion in ground_minions if minion.is_alive()]
        return alive_projectiles, alive_minions, alive_ground_minions

    def update_enemy_projectiles(
        self,
        player: Player,
        boss: Boss,
        minions: list[AerialMinion],
        enemy_projectiles: list[Projectile],
        dt: float,
    ) -> list[Projectile]:
        """Atualiza tiros do boss e dos minions voadores.

        Novos projeteis podem ser gerados no inicio do frame e entram na mesma
        etapa de simulacao dos tiros ja existentes.
        """
        self._add_enemy_projectile(enemy_projectiles, boss.try_attack(player))

        for minion in minions:
            self._add_enemy_projectile(enemy_projectiles, minion.try_attack(player))

        alive_projectiles: list[Projectile] = []
        for projectile in enemy_projectiles:
            projectile.update(dt)

            if projectile.rect.colliderect(player.rect):
                player.take_damage(projectile.damage)
                continue

            if projectile.is_visible():
                alive_projectiles.append(projectile)

        return alive_projectiles

    def update_boss_ults(
        self,
        player: Player,
        boss: Boss,
        ult_strikes: list[UltStrike],
        dt: float,
    ) -> list[UltStrike]:
        """Atualiza ULTs do boss, incluindo criacao, dano e limpeza."""
        new_strikes = boss.try_ult(player)
        if new_strikes:
            ult_strikes.extend(new_strikes)

        active_strikes: list[UltStrike] = []
        for strike in ult_strikes:
            strike.update(dt)

            if strike.can_hit() and strike.rect.colliderect(player.rect):
                player.take_damage(strike.damage)
                strike.has_hit = True

            if not strike.is_finished():
                active_strikes.append(strike)

        return active_strikes

    def update_aura_drops(
        self,
        player: Player,
        aura_drops: list[AuraDrop],
        dt: float,
    ) -> list[AuraDrop]:
        """Atualiza os orbs de aura e resolve coleta/expiracao."""
        alive_drops: list[AuraDrop] = []

        for drop in aura_drops:
            drop.update(dt)

            if drop.rect.colliderect(player.rect):
                player.gain_aura(drop.value)
                continue

            if not drop.is_expired():
                alive_drops.append(drop)

        return alive_drops

    def _resolve_player_projectile_hit(
        self,
        projectile: Projectile,
        boss: Boss,
        minions: list[AerialMinion],
        ground_minions: list[GroundMinion],
        aura_drops: list[AuraDrop],
    ) -> bool:
        """Resolve o primeiro alvo atingido por um tiro do player.

        O boss e testado primeiro porque ele e o alvo principal da run e o
        unico inimigo que gera aura ao sofrer dano.
        """
        if projectile.rect.colliderect(boss.rect):
            damage_dealt = boss.take_damage(projectile.damage)
            aura_drops.append(AuraDrop(boss.rect.centerx, boss.rect.bottom, damage_dealt))
            return True

        for enemy_group in (minions, ground_minions):
            for enemy in enemy_group:
                if projectile.rect.colliderect(enemy.rect):
                    enemy.take_damage(projectile.damage)
                    return True

        return False

    @staticmethod
    def _add_enemy_projectile(
        enemy_projectiles: list[Projectile],
        projectile: Projectile | None,
    ) -> None:
        """Adiciona um projetil inimigo apenas quando ele existir."""
        if projectile is not None:
            enemy_projectiles.append(projectile)
