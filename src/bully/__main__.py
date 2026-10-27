"""Demonstração dos dois cenários do laboratório.

Execute a partir da raiz do projeto, com o pacote instalado ou com
``PYTHONPATH=src python -m bully``.
"""

from __future__ import annotations

from bully.scenarios import cenario_figura_520, cenario_recuperacao_p7


def main() -> None:
    print("Cenário 1 — Figura 5.20: P7 falha e P4 inicia a eleição")
    print()
    figura = cenario_figura_520()
    figura.show_state()
    print()
    figura.show_history()
    print()
    print("Cenário 2 — P7 recupera e volta a ser o coordenador")
    print()
    recuperacao = cenario_recuperacao_p7()
    recuperacao.show_state()
    print()
    recuperacao.show_history()


if __name__ == "__main__":
    main()
