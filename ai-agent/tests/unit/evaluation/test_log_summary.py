import json

from venergy_agent.evaluation.log_summary import format_summary, summarize


def line(status, **extra):
    return json.dumps({"request_id": "r", "step": "resposta", "status": status, **extra})


def test_counts_only_the_reasons_the_plan_tracks_and_skips_other_lines():
    lines = [
        line("verificacao_numerica_falhou", attempt=1),
        line("verificacao_numerica_falhou", attempt=2),
        line("unidade_errada_na_resposta"),
        line("sem_tempo_para_narrar"),
        line("ok"),
        "uma linha que não é JSON",
        "",
    ]

    counts = summarize(lines)

    assert counts == {
        "verificacao_numerica_falhou": 2,
        "unidade_errada_na_resposta": 1,
        "sem_tempo_para_narrar": 1,
    }


def test_the_summary_lists_every_reason_even_when_zero():
    text = format_summary(summarize([line("periodo_nao_informado")]))

    assert "periodo_nao_informado: 1" in text
    assert "verificacao_numerica_falhou: 0" in text
    assert "unidade_errada_na_resposta: 0" in text
