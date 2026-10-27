"""Cenários didáticos do algoritmo Bully.

Os identificadores são os da Figura 5.20 de Tanenbaum & Van Steen:
P0 a P7, com P7 coordenador no início.
"""

from __future__ import annotations

from bully.simulator import BullySimulator


def cenario_figura_520() -> BullySimulator:
    """P7 falha, P4 detecta a falha e P6 vence a eleição."""

    simulator = BullySimulator(n=8)
    simulator.fail_process(7)
    simulator.start_election(4)
    return simulator


def cenario_recuperacao_p7() -> BullySimulator:
    """Depois da Figura 5.20, P7 volta e reassume a coordenação.

    P7 é o maior identificador ativo, então não há processo superior.
    Ele vence e envia COORDINATOR para P0..P6.
    """

    simulator = cenario_figura_520()
    simulator.recover_process(7)
    return simulator
