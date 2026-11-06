"""Resume o log da API por motivo de recusa da narrativa (T7 do plano de robustez).

Lê linhas JSON (uma por evento) de um arquivo, como as que application/ask.py grava, e conta
os motivos que o plano acompanha. Não lê perguntas nem respostas: só os status.
"""

import json
import sys
from collections import Counter
from collections.abc import Iterable

REASONS = (
    "verificacao_numerica_falhou",
    "unidade_errada_na_resposta",
    "periodo_ausente_na_resposta",
    "sem_tempo_para_narrar",
    "periodo_nao_informado",
    "narrativa_falhou",
    "pergunta_completada",
    "narrativa_ok",
)


def summarize(lines: Iterable[str]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for raw in lines:
        text = raw.strip()
        if not text.startswith("{"):
            continue
        try:
            status = json.loads(text).get("status")
        except json.JSONDecodeError:
            continue
        if status in REASONS:
            counts[status] += 1
    return dict(counts)


def format_summary(counts: dict[str, int]) -> str:
    return "\n".join(f"{reason}: {counts.get(reason, 0)}" for reason in REASONS) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("uso: python -m venergy_agent.evaluation.log_summary ARQUIVO_DE_LOG", file=sys.stderr)
        return 2
    with open(argv[0], encoding="utf-8") as file:
        print(format_summary(summarize(file)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
