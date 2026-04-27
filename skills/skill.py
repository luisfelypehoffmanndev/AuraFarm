"""Base para habilidades do player com sistema de cooldown."""

from abc import ABC, abstractmethod


class Skill(ABC):
    """Contrato minimo para skills com recarga.

    A classe base isola o conceito de cooldown para que cada skill concreta
    precise implementar apenas sua regra de ativacao.
    """

    def __init__(self, cooldown: float) -> None:
        """Inicializa cooldown total e o timer atual."""
        self.cooldown = cooldown
        self.cooldown_timer = 0.0

    def update(self, dt: float) -> None:
        """Reduz o timer de cooldown ate a skill ficar disponivel."""
        if self.cooldown_timer > 0:
            self.cooldown_timer = max(0.0, self.cooldown_timer - dt)

    def is_ready(self) -> bool:
        """Retorna se a skill pode ser usada agora."""
        return self.cooldown_timer == 0.0

    @abstractmethod
    def activate(self) -> None:
        """Executa a logica principal da skill."""
        pass
