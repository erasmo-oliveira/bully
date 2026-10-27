"""Processo participante de uma eleição Bully.

Cada processo guarda o próprio identificador, se está ativo, se é o
coordenador e se já entrou em uma eleição. A ordem de entrega fica no
simulador: o processo só decide como reagir a cada mensagem.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bully.message import Message, MessageType

if TYPE_CHECKING:
    from bully.simulator import BullySimulator


class Process:
    """Um processo Pk, com id(Pk) = k."""

    def __init__(self, process_id: int, simulator: BullySimulator) -> None:
        self.id = process_id
        self.simulator = simulator
        self.active = True
        self.is_coordinator = False
        self.election_in_progress = False
        self.coordinator_id: int | None = None
        self.election_id: int | None = None

    def start_election(self) -> None:
        """Entra na eleição, se estiver ativo.

        Isto apenas agenda o processo. Quem dispara a entrega das mensagens
        é `BullySimulator.start_election` ou `BullySimulator.recover_process`.
        """

        if not self.active:
            return
        self.simulator.schedule_election(self.id)

    def receive_election(self, message: Message) -> None:
        """Responde OK e, se ainda não participa, inicia a própria eleição.

        Só um processo de identificador maior responde. O algoritmo exige
        as duas ações: o OK avisa o remetente para desistir, e a eleição
        própria propaga a disputa para cima.
        """

        if not self.active or self.id <= message.sender:
            return
        self.simulator.send_message(
            Message(
                type=MessageType.OK,
                sender=self.id,
                receiver=message.sender,
                election_id=message.election_id,
                seq=0,
            )
        )
        if not self.election_in_progress:
            self.start_election()

    def receive_ok(self, message: Message) -> None:
        """Abandona a eleição. Um único OK basta."""

        if not self.active or not self.election_in_progress:
            return
        self.election_in_progress = False
        self.simulator.log(
            f"[ELECTION] P{self.id} encerra a eleição ao receber OK de P{message.sender}",
            kind="ELECTION",
        )

    def receive_coordinator(self, message: Message) -> None:
        """Registra o vencedor. Só o remetente da mensagem é coordenador."""

        if not self.active:
            return
        self.coordinator_id = message.sender
        self.is_coordinator = self.id == message.sender
        self.election_in_progress = False

    def recover(self) -> None:
        """Volta à execução e inicia uma eleição nova."""

        self.active = True
        self.is_coordinator = False
        self.election_in_progress = False
        self.start_election()

    def __repr__(self) -> str:
        return (
            f"Process(id={self.id}, active={self.active}, "
            f"is_coordinator={self.is_coordinator}, "
            f"election_in_progress={self.election_in_progress}, "
            f"coordinator_id={self.coordinator_id})"
        )
