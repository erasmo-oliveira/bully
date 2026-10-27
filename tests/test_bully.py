"""Testes do laboratório do algoritmo Bully."""

from __future__ import annotations

import pytest

from bully.message import Message, MessageType
from bully.scenarios import cenario_figura_520, cenario_recuperacao_p7
from bully.simulator import BullySimulator
from bully.__main__ import main

FIGURA_520 = """\
[FAIL] P7 falhou
=== Etapa A ===
[ELECTION] P4 inicia eleição
[MSG] P4 -> P5 : ELECTION
[MSG] P4 -> P6 : ELECTION
=== Etapa B ===
[MSG] P5 -> P4 : OK
[ELECTION] P4 encerra a eleição ao receber OK de P5
[MSG] P6 -> P4 : OK
=== Etapa C ===
[ELECTION] P5 inicia eleição
[MSG] P5 -> P6 : ELECTION
[ELECTION] P6 inicia eleição
[ELECTION] P6 não encontrou processo superior ativo
=== Etapa D ===
[MSG] P6 -> P5 : OK
[ELECTION] P5 encerra a eleição ao receber OK de P6
=== Etapa E ===
[MSG] P6 -> P0 : COORDINATOR
[MSG] P6 -> P1 : COORDINATOR
[MSG] P6 -> P2 : COORDINATOR
[MSG] P6 -> P3 : COORDINATOR
[MSG] P6 -> P4 : COORDINATOR
[MSG] P6 -> P5 : COORDINATOR
[COORD] P6 é o coordenador"""

MENSAGENS_FIGURA_520 = [
    ("ELECTION", 4, 5, 1),
    ("ELECTION", 4, 6, 1),
    ("OK", 5, 4, 1),
    ("OK", 6, 4, 1),
    ("ELECTION", 5, 6, 2),
    ("OK", 6, 5, 2),
    ("COORDINATOR", 6, 0, 3),
    ("COORDINATOR", 6, 1, 3),
    ("COORDINATOR", 6, 2, 3),
    ("COORDINATOR", 6, 3, 3),
    ("COORDINATOR", 6, 4, 3),
    ("COORDINATOR", 6, 5, 3),
]


def _assinatura(simulator: BullySimulator) -> list[tuple[str, int, int, int]]:
    return [
        (message.type.value, message.sender, message.receiver, message.election_id)
        for message in simulator.messages
    ]


def _coordenador_e_o_maior_ativo(simulator: BullySimulator) -> None:
    ativos = [process.id for process in simulator.processes if process.active]
    coordenador = max(ativos)
    assert simulator.get_coordinator() == coordenador
    for process in simulator.processes:
        if not process.active:
            assert process.is_coordinator is False
            assert process.election_in_progress is False
            continue
        assert process.coordinator_id == coordenador
        assert process.is_coordinator is (process.id == coordenador)
        assert process.election_in_progress is False


def test_estado_inicial_elege_o_maior_identificador() -> None:
    simulator = BullySimulator(n=8)
    assert simulator.get_coordinator() == 7
    assert all(process.active for process in simulator.processes)
    assert simulator.processes[7].is_coordinator is True
    assert simulator.message_trace() == []
    assert simulator.format_history() == ""


def test_figura_520_p4_detecta_falha_de_p7_e_p6_vence() -> None:
    simulator = cenario_figura_520()

    assert _assinatura(simulator) == MENSAGENS_FIGURA_520
    assert simulator.message_trace() == [
        (tipo, remetente, destinatario)
        for tipo, remetente, destinatario, _eleicao in MENSAGENS_FIGURA_520
    ]
    assert [message.seq for message in simulator.messages] == list(range(1, 13))
    assert all(message.sender != 7 and message.receiver != 7 for message in simulator.messages)
    assert simulator.format_history() == FIGURA_520
    _coordenador_e_o_maior_ativo(simulator)
    assert simulator.processes[7].active is False


def test_p7_inativo_nao_e_coordenador_nem_candidato() -> None:
    simulator = BullySimulator(n=8)
    simulator.fail_process(7)

    assert simulator.get_coordinator() is None
    assert simulator.processes[7].active is False
    assert simulator.processes[7].is_coordinator is False

    simulator.start_election(7)
    assert simulator.get_coordinator() is None
    assert simulator.message_trace() == []
    assert "P7 está inativo e não inicia eleição" in simulator.format_history()


def test_recuperacao_de_p7_devolve_a_coordenacao_ao_maior_id() -> None:
    simulator = cenario_recuperacao_p7()
    coordenadores = [
        message
        for message in simulator.messages
        if message.type is MessageType.COORDINATOR and message.sender == 7
    ]

    assert [message.receiver for message in coordenadores] == list(range(7))
    assert len({message.election_id for message in coordenadores}) == 1
    assert "P7 não encontrou processo superior ativo" in simulator.format_history()
    assert "[COORD] P7 é o coordenador" in simulator.format_history()
    _coordenador_e_o_maior_ativo(simulator)


def test_processo_que_retorna_sem_ser_o_maior_nao_assume() -> None:
    simulator = cenario_figura_520()
    simulator.fail_process(3)
    assert simulator.get_coordinator() == 6

    simulator.recover_process(3)

    assert simulator.processes[3].active is True
    assert ("ELECTION", 3, 4) in simulator.message_trace()
    assert ("ELECTION", 3, 5) in simulator.message_trace()
    assert ("ELECTION", 3, 6) in simulator.message_trace()
    _coordenador_e_o_maior_ativo(simulator)


def test_falha_de_p6_leva_a_vitoria_de_p5() -> None:
    simulator = cenario_figura_520()
    antes = len(simulator.messages)
    simulator.fail_process(6)
    simulator.start_election(4)
    novas = simulator.message_trace()[antes:]

    assert simulator.get_coordinator() == 5
    assert ("ELECTION", 4, 5) in novas
    assert ("OK", 5, 4) in novas
    assert [("COORDINATOR", 5, destino) for destino in range(5)] == [
        mensagem for mensagem in novas if mensagem[0] == "COORDINATOR"
    ]
    assert all(mensagem[2] not in (6, 7) for mensagem in novas)
    _coordenador_e_o_maior_ativo(simulator)


def test_mensagem_para_processo_inativo_e_descartada_sem_alterar_estado() -> None:
    simulator = BullySimulator(n=8)
    simulator.fail_process(7)
    antes = [
        (
            process.id,
            process.active,
            process.is_coordinator,
            process.election_in_progress,
            process.coordinator_id,
        )
        for process in simulator.processes
    ]

    simulator.send_message(
        Message(
            type=MessageType.ELECTION,
            sender=4,
            receiver=7,
            election_id=1,
            seq=0,
        )
    )

    depois = [
        (
            process.id,
            process.active,
            process.is_coordinator,
            process.election_in_progress,
            process.coordinator_id,
        )
        for process in simulator.processes
    ]
    historico = simulator.format_history()
    assert antes == depois
    assert "[MSG] P4 -> P7 : ELECTION" in historico
    assert "[DROP] P7 está inativo" in historico
    assert simulator.processes[4].election_in_progress is False


def test_reset_restaura_p7_e_apaga_o_historico() -> None:
    simulator = cenario_figura_520()
    simulator.reset()

    assert simulator.get_coordinator() == 7
    assert simulator.message_trace() == []
    assert simulator.format_history() == ""
    assert simulator.events == []
    assert all(process.active for process in simulator.processes)
    assert simulator.processes[7].is_coordinator is True
    assert all(process.coordinator_id == 7 for process in simulator.processes)


def test_recuperar_processo_ja_ativo_nao_abre_eleicao() -> None:
    simulator = BullySimulator(n=8)
    simulator.recover_process(3)

    assert simulator.get_coordinator() == 7
    assert simulator.message_trace() == []
    assert "[RECOVER] P3 já está ativo" in simulator.format_history()


def test_um_unico_processo_vence_sem_destinatarios() -> None:
    simulator = BullySimulator(n=1)
    simulator.start_election(0)

    assert simulator.get_coordinator() == 0
    assert simulator.message_trace() == []
    assert "[COORD] P0 é o coordenador" in simulator.format_history()
    _coordenador_e_o_maior_ativo(simulator)


def test_identificador_inexistente_e_recusado() -> None:
    simulator = BullySimulator(n=8)
    with pytest.raises(ValueError, match="processo inexistente"):
        simulator.fail_process(8)
    with pytest.raises(ValueError, match="processo inexistente"):
        simulator.start_election(-1)


def test_n_menor_que_um_e_recusado() -> None:
    with pytest.raises(ValueError, match="ao menos um processo"):
        BullySimulator(n=0)


def test_demo_imprime_os_dois_coordenadores(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    saida = capsys.readouterr().out
    assert "Coordenador atual: P6" in saida
    assert "Coordenador atual: P7" in saida
    assert "[COORD] P6 é o coordenador" in saida
    assert "[COORD] P7 é o coordenador" in saida
    assert "=== Etapa A ===" in saida
    assert "=== Etapa E ===" in saida
