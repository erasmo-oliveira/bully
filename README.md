# Laboratório do algoritmo Bully

Simulação didática, em Python, do algoritmo de eleição do valentão (Bully Algorithm), descrito por Garcia-Molina e apresentado por Tanenbaum e Van Steen na seção 5.4.1.

Há N processos, `P0` … `P(N-1)`, com `id(Pk) = k`. O coordenador é sempre o processo **ativo** de maior identificador. A detecção da falha fica fora do algoritmo: o programa chama `fail_process` e, em seguida, `start_election` no processo que percebeu a ausência do coordenador.

A simulação é determinística e roda em um único processo Python. Não há threads, rede nem timeout real. Processo inativo não recebe mensagem, não responde e não é candidato.

## Regras

Quando `Pk` inicia uma eleição:

1. Envia `ELECTION` a todo processo ativo com identificador maior que `k`.
2. Se ninguém responder, `Pk` vence.
3. Se alguém responder `OK`, `Pk` abandona a eleição.
4. Quem respondeu `OK` inicia a própria eleição, se ainda não estiver participando.
5. O vencedor envia `COORDINATOR` aos demais processos ativos.
6. Um processo que estava inativo, ao voltar, inicia uma eleição nova. Se for o maior identificador ativo, torna-se o coordenador.

## Como executar

Requer Python 3.10 ou superior. O `pip` que vem com o sistema pode ser antigo demais para instalação editável (PEP 660); o primeiro comando atualiza o pip só na conta do usuário.

```bash
python3 -m pip install --user -U 'pip>=23.1'
python3 -m pip install --user -e ".[dev]"
python3 -m pytest
python3 -m bully
```

Sem instalar o pacote:

```bash
PYTHONPATH=src python3 -m bully
PYTHONPATH=src python3 -m pytest
```

## Cenário da Figura 5.20

Estado inicial: `P0` … `P7` ativos e `P7` coordenador.

```python
from bully import BullySimulator

sim = BullySimulator(n=8)
sim.fail_process(7)
sim.start_election(4)
sim.get_coordinator()  # 6
sim.show_state()
sim.show_history()
```

`P7` está inativo, então `P4` só escreve para `P5` e `P6`:

| Etapa | O que acontece |
| --- | --- |
| A | `P4` envia `ELECTION` a `P5` e `P6` |
| B | `P5` e `P6` respondem `OK`; `P4` encerra a eleição |
| C | `P5` envia `ELECTION` a `P6`; `P6` não tem superior ativo |
| D | `P6` responde `OK` a `P5` |
| E | `P6` envia `COORDINATOR` a `P0` … `P5` e assume a coordenação |

O histórico sai agrupado nessas etapas. Uma linha `[DROP]` aparece quando alguma mensagem é endereçada a um processo inativo.

## Recuperação de P7

```python
sim.recover_process(7)
sim.get_coordinator()  # 7
```

`P7` volta, não encontra processo ativo com identificador maior, vence e envia `COORDINATOR` a `P0` … `P6`.

Os dois cenários também estão em `bully.scenarios` e rodam com `python3 -m bully`.

## Mapa do código

```text
src/bully/message.py     tipos ELECTION, OK e COORDINATOR
src/bully/process.py     estado e reação de cada processo
src/bully/simulator.py   ondas de mensagens, falhas e histórico
src/bully/scenarios.py   Figura 5.20 e recuperação de P7
tests/test_bully.py      rastros de mensagens e estados
```

`Message` carrega tipo, remetente, destinatário, `election_id` e `seq`. O simulador numera `seq` na ordem de emissão.

## O que vale a pena alterar

- Quem detecta a falha: troque `start_election(4)` por outro processo ativo.
- Mais de uma falha: `fail_process(6)` depois da eleição e inicie outra. O maior identificador que restar vence.
- Recuperação de um processo que não é o maior: derrube `P3`, recupere-o e observe que a eleição termina de novo no maior ativo.
- Leia `Process.receive_election` e `BullySimulator._run_wave` lado a lado. O processo decide a resposta; o simulador segura a vitória até a onda de `OK` terminar, para a ordem bater com a figura.
# bully
