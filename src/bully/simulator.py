"""Simulador determinístico do algoritmo Bully.

As mensagens de uma mesma leva são entregues em ondas. Dentro de cada onda
acontecem três passos, nesta ordem:

1. cada iniciador envia ELECTION aos processos ativos de id maior;
2. esses processos respondem OK;
3. só então quem não recebeu OK se declara vencedor e envia COORDINATOR.

Essa separação reproduz as etapas da Figura 5.20. Uma fila que declarasse
a vitória no instante em que o processo não encontra ninguém acima faria
P6 anunciar o coordenador antes de responder OK a P5.
"""

from __future__ import annotations

from dataclasses import dataclass

from bully.message import Message, MessageType
from bully.process import Process


@dataclass
class Event:
    """Uma linha observável da simulação."""

    kind: str
    text: str
    stage: str | None = None
    message: Message | None = None


class BullySimulator:
    """Cria os processos, entrega as mensagens e guarda o histórico."""

    def __init__(self, n: int = 8) -> None:
        if n < 1:
            raise ValueError("a simulação precisa de ao menos um processo")
        self.n = n
        self.processes: list[Process] = []
        self.events: list[Event] = []
        self.messages: list[Message] = []
        self._pending_initiators: list[int] = []
        self._seq = 0
        self._next_election_id = 1
        self._stage_index = 0
        self._current_stage: str | None = None
        self._draining = False
        self.create_processes()

    def create_processes(self) -> None:
        """Cria P0..P(n-1). O maior identificador começa como coordenador."""

        self.processes = [Process(process_id, self) for process_id in range(self.n)]
        coordinator_id = self.n - 1
        for process in self.processes:
            process.coordinator_id = coordinator_id
        self.processes[coordinator_id].is_coordinator = True

    def fail_process(self, process_id: int) -> None:
        """Desativa um processo. Ele deixa de ser candidato e coordenador."""

        process = self._process(process_id)
        process.active = False
        process.is_coordinator = False
        process.election_in_progress = False
        self._pending_initiators = [
            initiator for initiator in self._pending_initiators if initiator != process_id
        ]
        self.log(f"[FAIL] P{process_id} falhou", kind="FAIL")

    def recover_process(self, process_id: int) -> None:
        """Reativa um processo. Ao voltar, ele inicia uma eleição."""

        process = self._process(process_id)
        if process.active:
            self.log(f"[RECOVER] P{process_id} já está ativo", kind="RECOVER")
            return
        self.log(f"[RECOVER] P{process_id} recuperou", kind="RECOVER")
        process.recover()
        self._drain()

    def get_coordinator(self) -> int | None:
        """Identificador do coordenador ativo, ou None se não houver."""

        for process in self.processes:
            if process.active and process.is_coordinator:
                return process.id
        return None

    def start_election(self, process_id: int) -> None:
        """O processo indicado percebe a falha e abre uma eleição."""

        process = self._process(process_id)
        if not process.active:
            self.log(
                f"[ELECTION] P{process_id} está inativo e não inicia eleição",
                kind="ELECTION",
            )
            return
        process.start_election()
        self._drain()

    def schedule_election(self, process_id: int) -> None:
        """Agenda um processo para a próxima onda, sem entregar mensagens ainda.

        Usado por `Process`. Chamar `start_election` ou `recover_process`
        executa as ondas pendentes.
        """

        process = self._process(process_id)
        if not process.active or process.election_in_progress:
            return
        process.election_in_progress = True
        process.election_id = self._next_election_id
        self._next_election_id += 1
        self._pending_initiators.append(process_id)

    def send_message(self, message: Message) -> None:
        """Entrega uma mensagem, ou registra DROP se o destino está inativo."""

        self._process(message.sender)
        receiver = self._process(message.receiver)
        stamped = self._accept(message)
        if not receiver.active:
            self.log(f"[DROP] P{receiver.id} está inativo", kind="DROP")
            return
        self._dispatch(stamped)
        self._drain()

    def broadcast(
        self,
        sender_id: int,
        message_type: MessageType,
        election_id: int,
    ) -> None:
        """Envia a mesma mensagem a todos os processos ativos, exceto o remetente."""

        self._process(sender_id)
        for process in self.processes:
            if process.id == sender_id or not process.active:
                continue
            self.send_message(
                Message(
                    type=message_type,
                    sender=sender_id,
                    receiver=process.id,
                    election_id=election_id,
                    seq=0,
                )
            )

    def higher_active_ids(self, process_id: int) -> list[int]:
        """Identificadores ativos estritamente maiores que `process_id`."""

        self._process(process_id)
        return [
            process.id
            for process in self.processes
            if process.active and process.id > process_id
        ]

    def show_state(self) -> None:
        """Imprime o estado atual dos processos."""

        print(self.format_state())

    def show_history(self) -> None:
        """Imprime o histórico agrupado em etapas."""

        print(self.format_history())

    def format_state(self) -> str:
        """Estado atual, pronto para impressão ou comparação em teste."""

        coordinator = self.get_coordinator()
        if coordinator is None:
            lines = ["Coordenador atual: nenhum"]
        else:
            lines = [f"Coordenador atual: P{coordinator}"]
        for process in self.processes:
            situation = "ativo" if process.active else "inativo"
            role = " coordenador" if process.is_coordinator else ""
            election = " eleição_em_andamento" if process.election_in_progress else ""
            if process.coordinator_id is None:
                known = " conhece=nenhum"
            else:
                known = f" conhece=P{process.coordinator_id}"
            lines.append(f"P{process.id} {situation}{role}{election}{known}")
        return "\n".join(lines)

    def format_history(self) -> str:
        """Histórico com cabeçalhos `=== Etapa A ===`, `=== Etapa B ===`, ..."""

        lines: list[str] = []
        current_stage: str | None = None
        started = False
        for event in self.events:
            if not started or event.stage != current_stage:
                started = True
                current_stage = event.stage
                if event.stage is not None:
                    lines.append(f"=== Etapa {event.stage} ===")
            lines.append(event.text)
        return "\n".join(lines)

    def message_trace(self) -> list[tuple[str, int, int]]:
        """Sequência (tipo, remetente, destinatário) na ordem de emissão."""

        return [
            (message.type.value, message.sender, message.receiver)
            for message in self.messages
        ]

    def reset(self) -> None:
        """Volta ao estado inicial: todos ativos, maior id coordenador, histórico vazio."""

        self._seq = 0
        self._next_election_id = 1
        self._stage_index = 0
        self._current_stage = None
        self._draining = False
        self._pending_initiators.clear()
        self.events.clear()
        self.messages.clear()
        self.create_processes()

    def log(self, text: str, *, kind: str = "INFO", message: Message | None = None) -> None:
        """Acrescenta uma linha ao histórico, na etapa corrente."""

        self.events.append(
            Event(kind=kind, text=text, stage=self._current_stage, message=message)
        )

    def _process(self, process_id: int) -> Process:
        if process_id < 0 or process_id >= len(self.processes):
            raise ValueError(f"processo inexistente: {process_id}")
        return self.processes[process_id]

    def _accept(self, message: Message) -> Message:
        stamped = self._stamp(message)
        self.messages.append(stamped)
        self.log(
            f"[MSG] P{stamped.sender} -> P{stamped.receiver} : {stamped.type.value}",
            kind="MSG",
            message=stamped,
        )
        return stamped

    def _stamp(self, message: Message) -> Message:
        self._seq += 1
        return Message(
            type=message.type,
            sender=message.sender,
            receiver=message.receiver,
            election_id=message.election_id,
            seq=self._seq,
        )

    def _dispatch(self, message: Message) -> None:
        receiver = self.processes[message.receiver]
        if message.type is MessageType.ELECTION:
            receiver.receive_election(message)
        elif message.type is MessageType.OK:
            receiver.receive_ok(message)
        elif message.type is MessageType.COORDINATOR:
            receiver.receive_coordinator(message)
        else:
            raise ValueError(f"tipo de mensagem desconhecido: {message.type}")

    def _drain(self) -> None:
        """Executa as ondas já agendadas.

        `_draining` impede que a resposta OK de uma mensagem dispare a onda
        seguinte antes de todos os ELECTION desta onda serem entregues.
        """

        if self._draining:
            return
        self._draining = True
        try:
            while self._pending_initiators:
                self._run_wave()
        finally:
            self._draining = False
            self._current_stage = None

    def _run_wave(self) -> None:
        starters = sorted(set(self._pending_initiators))
        self._pending_initiators.clear()
        active_starters = [
            self.processes[process_id]
            for process_id in starters
            if self.processes[process_id].active
            and self.processes[process_id].election_in_progress
        ]
        if not active_starters:
            return

        self._open_stage()
        elections: list[Message] = []
        asked_someone: set[int] = set()
        for process in active_starters:
            self.log(f"[ELECTION] P{process.id} inicia eleição", kind="ELECTION")
            higher = self.higher_active_ids(process.id)
            election_id = process.election_id
            if election_id is None:
                raise RuntimeError(f"P{process.id} entrou na eleição sem identificador")
            if not higher:
                self.log(
                    f"[ELECTION] P{process.id} não encontrou processo superior ativo",
                    kind="ELECTION",
                )
                continue
            asked_someone.add(process.id)
            for higher_id in higher:
                elections.append(
                    self._accept(
                        Message(
                            type=MessageType.ELECTION,
                            sender=process.id,
                            receiver=higher_id,
                            election_id=election_id,
                            seq=0,
                        )
                    )
                )

        if elections:
            self._open_stage()
            for message in elections:
                receiver = self.processes[message.receiver]
                if not receiver.active:
                    self.log(f"[DROP] P{receiver.id} está inativo", kind="DROP")
                    continue
                self._dispatch(message)

        winner_ids = [
            process.id
            for process in active_starters
            if process.active and process.election_in_progress
        ]
        if not winner_ids:
            return
        self._open_stage()
        for winner_id in winner_ids:
            if winner_id in asked_someone:
                self.log(
                    f"[ELECTION] P{winner_id} não recebeu OK e vence a eleição",
                    kind="ELECTION",
                )
            self._announce(winner_id)

    def _announce(self, winner_id: int) -> None:
        for process in self.processes:
            process.is_coordinator = False
        winner = self.processes[winner_id]
        winner.is_coordinator = True
        winner.coordinator_id = winner_id
        winner.election_in_progress = False
        election_id = winner.election_id
        if election_id is None:
            raise RuntimeError(f"P{winner_id} venceu sem identificador de eleição")
        self.broadcast(winner_id, MessageType.COORDINATOR, election_id)
        self.log(f"[COORD] P{winner_id} é o coordenador", kind="COORD")

    def _open_stage(self) -> str:
        label = _stage_label(self._stage_index)
        self._stage_index += 1
        self._current_stage = label
        return label


def _stage_label(index: int) -> str:
    """Converte 0, 1, 2... em A, B, C... e segue com AA depois de Z."""

    label = ""
    value = index
    while True:
        label = chr(ord("A") + value % 26) + label
        value = value // 26 - 1
        if value < 0:
            break
    return label
