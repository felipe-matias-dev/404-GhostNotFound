import pytest

from venergy_agent.config import AGENT_ROOT, REPO_ROOT
from venergy_agent.domain.wording import label
from venergy_agent.infrastructure.semantic_source import YamlSemanticLayerSource

UNACCENTED_WORDS = {
    "arrecadacao",
    "codigo",
    "competencia",
    "conexao",
    "decomposicao",
    "duracao",
    "eletronico",
    "instalacao",
    "interrupcao",
    "interrupcoes",
    "ligacao",
    "media",
    "medio",
    "municipio",
    "nao",
    "numero",
    "ocorrencia",
    "periodo",
    "potencia",
    "preco",
    "satisfacao",
    "ultima",
    "variacao",
}
COLUMNS_USERS_NAME_AS_IS = {
    "bairro",
    "causa",
    "cod_alimentador",
    "cod_medidor",
    "cod_ocorrencia",
    "cod_uc",
    "data_abertura",
    "data_conexao_gd",
    "data_encerramento",
    "data_fechamento",
    "data_instalacao",
    "data_ligacao",
    "data_pagamento",
    "data_ultima_troca",
    "data_vencimento",
    "modelo",
    "municipio",
    "periodo_atual",
    "periodo_base",
    "protocolo",
    "subassunto",
}


@pytest.fixture(scope="module")
def layer():
    import asyncio

    return asyncio.run(
        YamlSemanticLayerSource(
            AGENT_ROOT / "semantic" / "semantic_layer.yaml",
            REPO_ROOT / "contracts" / "gold_schema.yaml",
        ).load()
    )


def _columns(layer):
    return sorted({column.name for view in layer.views for column in view.columns})


def test_every_column_has_a_portuguese_label_with_accents_and_no_abbreviation(layer):
    for column in _columns(layer):
        words = label(column).split()
        assert "_" not in label(column), column
        assert not set(words) & UNACCENTED_WORDS, (column, label(column))
        assert words[0] != "n", (column, label(column))


def test_every_column_users_ask_about_is_in_the_glossary(layer):
    glossary = " ".join(
        f"{term.term} {' '.join(term.synonyms)} {term.maps_to}" for term in layer.glossary
    )
    missing = [
        column
        for column in _columns(layer)
        if column not in glossary and column not in COLUMNS_USERS_NAME_AS_IS
    ]

    assert missing == []


def test_the_glossary_knows_the_sector_acronyms(layer):
    terms = {name.lower() for term in layer.glossary for name in (term.term, *term.synonyms)}

    assert {"dec", "fec", "uc", "kwh", "alta tensão", "baixa tensão", "mês de referência"} <= terms


def test_a_percent_alias_is_labelled_in_words():
    assert label("participacao_receita_faturada_pct") == "participação receita faturada em %"
