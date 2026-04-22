"""Ponto de entrada do jogo Aura Farming."""

from game import Game


def main() -> None:
    """Cria a instancia principal do jogo e inicia o loop."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
