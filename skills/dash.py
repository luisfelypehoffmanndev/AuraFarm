"""Skill de deslocamento rapido do player."""

from skills.skill import Skill


class Dash(Skill):
    """Representa o dash horizontal usado para reposicionamento."""

    def __init__(self) -> None:
        super().__init__(cooldown=1.2)
        self.distance = 90
        self.last_direction = 1

    def activate(self) -> None:
        """Inicia o cooldown do dash."""
        self.cooldown_timer = self.cooldown
