"""Skill defensiva do player."""

from skills.skill import Skill


class Shield(Skill):
    """Ativa imunidade temporaria durante um curto periodo."""

    def __init__(self) -> None:
        """Inicializa cooldown, duracao da imunidade e timer ativo."""
        super().__init__(cooldown=3.0)
        self.duration = 1.2
        self.active_timer = 0.0

    def activate(self) -> None:
        """Liga o escudo e inicia seu cooldown."""
        self.cooldown_timer = self.cooldown
        self.active_timer = self.duration
