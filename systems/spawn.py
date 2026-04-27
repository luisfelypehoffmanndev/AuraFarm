"""Sistema responsavel pela manutencao e spawn dos minions."""

from __future__ import annotations

from entities.aerial_minion import AerialMinion
from entities.boss import Boss
from entities.ground_minion import GroundMinion
from entities.player import Player
from utils.constants import GROUND_MINION_MAX_ALIVE, GROUND_MINION_SPAWN_COOLDOWN


class SpawnSystem:
    """Concentra regras de spawn e update de inimigos auxiliares."""

    def update_aerial_minions(
        self,
        boss: Boss,
        minions: list[AerialMinion],
        dt: float,
    ) -> None:
        """Executa a politica de spawn e o update dos minions voadores."""
        self._spawn_aerial_minions(boss, minions)

        for minion in minions:
            minion.update(dt)

    def update_ground_minions(
        self,
        boss: Boss,
        player: Player,
        ground_minions: list[GroundMinion],
        ground_minion_spawn_timer: float,
        survival_time: float,
        dt: float,
    ) -> tuple[list[GroundMinion], float]:
        """Executa spawn, update, colisao e limpeza dos minions terrestres."""
        ground_minion_spawn_timer = max(0.0, ground_minion_spawn_timer - dt)
        max_alive = min(GROUND_MINION_MAX_ALIVE, max(0, (boss.phase + 1) // 3))

        ground_minion_spawn_timer = self._spawn_ground_minion_if_needed(
            boss,
            ground_minions,
            ground_minion_spawn_timer,
            max_alive,
            survival_time,
        )

        alive_minions: list[GroundMinion] = []
        for minion in ground_minions:
            minion.update(dt)

            if minion.rect.colliderect(player.rect):
                player.take_damage(minion.contact_damage)
                continue

            if not minion.is_offscreen() and minion.is_alive():
                alive_minions.append(minion)

        return alive_minions, ground_minion_spawn_timer

    def _spawn_aerial_minions(self, boss: Boss, minions: list[AerialMinion]) -> None:
        """Cria novos minions voadores seguindo as regras fornecidas pelo boss."""
        max_alive = boss.get_max_aerial_minions()
        if not boss.should_spawn_minion(len(minions)):
            return

        for x, y in boss.get_minion_spawn_positions():
            if len(minions) >= max_alive:
                break
            minions.append(AerialMinion(x, y, boss.phase))

    def _spawn_ground_minion_if_needed(
        self,
        boss: Boss,
        ground_minions: list[GroundMinion],
        ground_minion_spawn_timer: float,
        max_alive: int,
        survival_time: float,
    ) -> float:
        """Cria um minion terrestre quando houver espaco e cooldown livre."""
        if ground_minion_spawn_timer > 0 or len(ground_minions) >= max_alive:
            return ground_minion_spawn_timer

        from_left = (int(survival_time) // 2) % 2 == 0
        ground_minions.append(GroundMinion(from_left=from_left, phase=boss.phase))
        return max(4.8, GROUND_MINION_SPAWN_COOLDOWN - max(0, boss.phase - 2) * 0.45)
