"""Calibração do juiz (DEC-047): prepara a planilha às cegas e compara as notas.

`prepare` gera as respostas dos itens escolhidos na Gold real, grava a planilha que a pessoa
preenche sem ver as notas do juiz e guarda à parte as notas das rubricas pedidas. `compare` lê
as notas humanas e calcula o acordo. Tudo fica em eval/runs_gold/, fora do Git (DEC-024).
"""

import argparse
import asyncio
import csv
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from venergy_agent.bootstrap import build_agent
from venergy_agent.config import AgentSettings
from venergy_agent.domain.answer import AnswerStatus
from venergy_agent.domain.judge import PASS_SCORE
from venergy_agent.evaluation.__main__ import EVAL_DIR, load_set, runs_dir
from venergy_agent.infrastructure.answer_judge import PydanticAiAnswerJudge
from venergy_agent.infrastructure.llm import build_judge_model

MIN_SAME_PASSED_SHARE = 0.8
MAX_MEAN_ABSOLUTE_DIFFERENCE = 1.0
DEFAULT_IDS = "G106,G108,G110,G059,G063,G065,G089,G104,G109,G057,G138,G139,G140,G141,G143"


@dataclass(frozen=True)
class Agreement:
    items: int
    same_passed: int
    mean_absolute_difference: float
    mean_signed_difference: float

    @property
    def meets_criterion(self) -> bool:
        return (
            self.items > 0
            and self.same_passed / self.items >= MIN_SAME_PASSED_SHARE
            and self.mean_absolute_difference <= MAX_MEAN_ABSOLUTE_DIFFERENCE
        )


def agreement(judge: Mapping[str, int], human: Mapping[str, int]) -> Agreement:
    common = [item for item in judge if item in human]
    differences = [judge[item] - human[item] for item in common]
    same = sum((judge[item] >= PASS_SCORE) == (human[item] >= PASS_SCORE) for item in common)
    count = len(common)
    return Agreement(
        items=count,
        same_passed=same,
        mean_absolute_difference=sum(abs(d) for d in differences) / count if count else 0.0,
        mean_signed_difference=sum(differences) / count if count else 0.0,
    )


def read_human_scores(path: Path) -> dict[str, int]:
    with path.open(encoding="utf-8") as sheet:
        rows = csv.DictReader(sheet, delimiter=";")
        return {row["id"]: int(row["nota_humana"]) for row in rows if row["nota_humana"].strip()}


async def prepare(ids: Sequence[str], rubrics: Sequence[str]) -> Path:
    settings = AgentSettings()
    _, golden = load_set(EVAL_DIR / "golden_set.yaml")
    items = [item for item in golden if item["id"] in set(ids)]
    agent = await build_agent(settings)
    model = build_judge_model(settings)
    judges = {
        rubric: PydanticAiAnswerJudge(model, settings.prompts_dir / "judge", rubric)
        for rubric in rubrics
    }
    folder = runs_dir("gold_real") / f"calibracao-{datetime.now(UTC):%Y-%m-%dT%H%M%SZ}"
    folder.mkdir(parents=True)
    sheet_rows, scores, blind = [], {rubric: {} for rubric in rubrics}, []
    for item in items:
        answer = await agent.ask(item["question"], session_id=f"calibracao-{item['id']}")
        if answer.status is not AnswerStatus.ANSWERED:
            continue
        for rubric, judge in judges.items():
            run = await judge.judge(item["question"], answer)
            scores[rubric][item["id"]] = run.verdict.score
        blind.append(
            f"## {item['id']}\n\n**Pergunta:** {item['question']}\n\n**Resposta:**\n\n"
            f"{answer.answer}\n\n**Suposições:** {'; '.join(answer.assumptions) or 'nenhuma'}\n\n"
            "**Linhas:**\n\n```json\n"
            + json.dumps(list(answer.rows), ensure_ascii=False, default=str, indent=1)
            + "\n```\n"
        )
        sheet_rows.append({"id": item["id"], "nota_humana": ""})
    (folder / "para-avaliar.md").write_text(
        "# Calibração do juiz: avaliação às cegas\n\n"
        "Dê uma nota de 1 a 5 a cada resposta pela rubrica de prompts/judge/v2/judge.md "
        "(clareza, completude e fidelidade às linhas) e preencha notas.csv. Não abra "
        "notas-do-juiz.json antes de terminar.\n\n" + "\n".join(blind),
        encoding="utf-8",
    )
    with (folder / "notas.csv").open("w", encoding="utf-8", newline="") as sheet:
        writer = csv.DictWriter(sheet, fieldnames=["id", "nota_humana"], delimiter=";")
        writer.writeheader()
        writer.writerows(sheet_rows)
    (folder / "notas-do-juiz.json").write_text(
        json.dumps(scores, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return folder


def compare(folder: Path) -> list[str]:
    human = read_human_scores(folder / "notas.csv")
    judges = json.loads((folder / "notas-do-juiz.json").read_text(encoding="utf-8"))
    lines = []
    for rubric, scores in judges.items():
        result = agreement(scores, human)
        lines.append(
            f"{rubric}: {result.items} itens, passed igual em {result.same_passed}, "
            f"diferença média absoluta {result.mean_absolute_difference:.2f}, "
            f"com sinal {result.mean_signed_difference:+.2f}, "
            f"critério {'atingido' if result.meets_criterion else 'não atingido'}"
        )
    return lines


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m venergy_agent.evaluation.calibration")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--ids", default=DEFAULT_IDS)
    prepare_parser.add_argument("--rubrics", default="v1,v2")
    compare_parser = commands.add_parser("compare")
    compare_parser.add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        folder = asyncio.run(prepare(args.ids.split(","), args.rubrics.split(",")))
        print(f"planilha gravada em {folder} (fora do Git)")
        return 0
    print("\n".join(compare(args.folder)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
