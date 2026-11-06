from venergy_agent.domain.semantic import ColumnSpec, SemanticLayer, ViewSpec
from venergy_agent.infrastructure.categorical_values import (
    WithCategoricalValues,
    categorical_columns,
)

UC = ViewSpec(
    name="sem_uc",
    description="UCs",
    grain="uma linha por UC",
    columns=(
        ColumnSpec(name="cod_uc", type="text", description="código"),
        ColumnSpec(name="municipio", type="text", description="município"),
        ColumnSpec(name="bairro", type="text", description="bairro"),
        ColumnSpec(name="canal", type="text", description="canal"),
    ),
)
LAYER = SemanticLayer(version="t", views=(UC,))


class FixedSource:
    async def load(self):
        return LAYER


MANY_NAMES = tuple(f"Bairro {number}" for number in range(11))


async def test_many_values_become_hints_and_few_values_become_the_allowed_list():
    async def loader(columns):
        return {"bairro": MANY_NAMES, "canal": ("APP", "LOJA")}

    layer = await WithCategoricalValues(FixedSource(), loader).load()

    assert layer.categorical_values == {"bairro": MANY_NAMES}
    columns = {column.name: column for column in layer.views[0].columns}
    assert columns["canal"].allowed_values == ("APP", "LOJA")
    assert columns["bairro"].allowed_values == ()


async def test_a_loader_that_fails_leaves_the_layer_without_values():
    async def loader(columns):
        raise RuntimeError("banco fora")

    layer = await WithCategoricalValues(FixedSource(), loader).load()

    assert layer.categorical_values == {}


def test_only_known_text_columns_are_read_from_the_first_view_that_has_them():
    assert categorical_columns(LAYER) == {
        "municipio": "sem_uc",
        "bairro": "sem_uc",
        "canal": "sem_uc",
    }
