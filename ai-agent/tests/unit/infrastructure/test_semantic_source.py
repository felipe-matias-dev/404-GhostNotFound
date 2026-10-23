import copy

import pytest

from venergy_agent.config import AGENT_ROOT, REPO_ROOT
from venergy_agent.infrastructure.semantic_source import (
    SemanticLayerError,
    YamlSemanticLayerSource,
    build_layer,
    read_documents,
)

LAYER_PATH = AGENT_ROOT / "semantic" / "semantic_layer.yaml"
CONTRACT_PATH = REPO_ROOT / "contracts" / "gold_schema.yaml"


@pytest.fixture
def documents():
    layer, contract = read_documents(LAYER_PATH, CONTRACT_PATH)
    return copy.deepcopy(layer), copy.deepcopy(contract)


async def test_real_files_load_the_three_agent_views():
    layer = await YamlSemanticLayerSource(LAYER_PATH, CONTRACT_PATH).load()

    assert layer.allowed_views == frozenset(
        {"sem_uc", "sem_faturamento_mensal", "sem_continuidade_alimentador_mensal"}
    )


def test_relations_come_from_the_foreign_key_and_the_entity_keys(documents):
    layer = build_layer(*documents)

    links = {
        frozenset(
            {
                (relation.left_view, relation.left_column),
                (relation.right_view, relation.right_column),
            }
        )
        for relation in layer.relations
    }
    assert links == {
        frozenset({("sem_faturamento_mensal", "cod_uc"), ("sem_uc", "cod_uc")}),
        frozenset(
            {
                ("sem_uc", "cod_alimentador"),
                ("sem_continuidade_alimentador_mensal", "cod_alimentador"),
            }
        ),
    }


def test_each_link_appears_once_even_when_fk_and_shared_key_both_apply(documents):
    layer = build_layer(*documents)

    assert len(layer.relations) == 2


def test_competencia_is_not_a_join_key(documents):
    layer = build_layer(*documents)

    assert all(relation.left_column != "competencia" for relation in layer.relations)


def test_confirmed_column_types_and_allowed_values_come_from_the_contract(documents):
    layer = build_layer(*documents)

    classe = next(c for c in layer.views[0].columns if c.name == "classe")
    assert classe.type == "text"
    assert classe.allowed_values == ("B1", "B2", "B3", "A4")


def test_column_still_marked_a_confirmar_is_not_allowed(documents):
    layer, contract = documents
    contract["tables"]["gold_dim_uc"]["columns"]["municipio"]["status"] = "a_confirmar"

    with pytest.raises(SemanticLayerError, match="municipio.*a_confirmar"):
        build_layer(layer, contract)


def test_column_missing_from_the_contract_is_rejected(documents):
    layer, contract = documents
    layer["views"][0]["columns"].append({"name": "coluna_que_nao_existe", "description": "x"})

    with pytest.raises(SemanticLayerError, match="coluna_que_nao_existe"):
        build_layer(layer, contract)


def test_unknown_source_table_is_rejected(documents):
    layer, contract = documents
    layer["views"][0]["source"] = "gold_tabela_inventada"

    with pytest.raises(SemanticLayerError, match="gold_tabela_inventada"):
        build_layer(layer, contract)


def test_view_without_its_primary_key_is_rejected(documents):
    layer, contract = documents
    layer["views"][0]["columns"] = [
        column for column in layer["views"][0]["columns"] if column["name"] != "cod_uc"
    ]

    with pytest.raises(SemanticLayerError, match="chave primária 'cod_uc'"):
        build_layer(layer, contract)


def test_primary_key_that_is_not_confirmed_blocks_the_view(documents):
    layer, contract = documents
    contract["tables"]["gold_dim_uc"]["columns"]["cod_uc"]["status"] = "a_confirmar"

    with pytest.raises(SemanticLayerError, match="cod_uc.*não está confirmada"):
        build_layer(layer, contract)


def test_view_name_must_start_with_sem(documents):
    layer, contract = documents
    layer["views"][0]["name"] = "uc"

    with pytest.raises(SemanticLayerError, match="sem_"):
        build_layer(layer, contract)


def test_sample_row_with_a_value_outside_the_contract_is_rejected(documents):
    layer, contract = documents
    layer["views"][0]["sample_rows"] = [{"cod_uc": "1", "classe": "Residencial"}]

    with pytest.raises(SemanticLayerError, match="Residencial"):
        build_layer(layer, contract)


def test_every_problem_is_reported_together(documents):
    layer, contract = documents
    layer["views"][0]["source"] = "gold_tabela_inventada"
    layer["views"][1]["name"] = "faturamento"

    with pytest.raises(SemanticLayerError) as error:
        build_layer(layer, contract)

    assert len(error.value.problems) == 2
