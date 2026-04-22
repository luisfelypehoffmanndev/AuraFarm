"""Skill de disparo do player."""

from skills.skill import Skill


class Shot(Skill):
    """Controla cooldown e dano do tiro basico."""

    def __init__(self) -> None:
        super().__init__(cooldown=0.35)
        self.damage = 10

    def activate(self) -> None:
        """Consome a skill e inicia a recarga."""
        self.cooldown_timer = self.cooldown
