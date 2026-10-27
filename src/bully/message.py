"""Mensagens do algoritmo Bully.

As três mensagens do algoritmo são ELECTION, OK e COORDINATOR.
O simulador preenche `seq` com um contador global. `election_id` identifica
qual eleição produziu a mensagem, para o histórico continuar legível quando
há mais de uma eleição em sequência.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MessageType(Enum):
    """Tipos fundamentais do algoritmo de Garcia-Molina."""

    ELECTION = "ELECTION"
    OK = "OK"
    COORDINATOR = "COORDINATOR"


@dataclass(frozen=True)
class Message:
    """Uma mensagem de um processo para outro.

    `seq` é atribuído pelo simulador no momento do envio. O valor passado
    pelo chamador é substituído, para a numeração permanecer única.
    """

    type: MessageType
    sender: int
    receiver: int
    election_id: int
    seq: int

    def __str__(self) -> str:
        return f"P{self.sender} -> P{self.receiver} : {self.type.value}"
