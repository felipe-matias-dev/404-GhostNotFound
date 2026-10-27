import pytest
from pydantic import ValidationError

from venergy_agent.domain.semantic import ColumnSpec, Relation, SemanticLayer, ViewSpec


@pytest.fixture
def views():
    uc = ViewSpec(
        name="sem_uc",
        description="Unidades consumidoras",
        grain="uma linha por UC",
        columns=(ColumnSpec(name="cod_uc", type="text", description="código da UC"),),
    )
    faturamento = ViewSpec(
        name="sem_faturamento_mensal",
        description="Faturamento mensal",
        grain="UC por competência",
        columns=(
            ColumnSpec(name="cod_uc", type="text", description="código da UC"),
            ColumnSpec(name="competencia", type="text", description="YYYY-MM"),
        ),
    )
    return (uc, faturamento)


def test_allowed_views_lists_view_names(views):
    layer = SemanticLayer(version="v0", views=views)

    assert layer.allowed_views == frozenset({"sem_uc", "sem_faturamento_mensal"})


@pytest.mark.parametrize(
    "relation",
    [
        Relation(
            left_view="sem_x", left_column="cod_uc", right_view="sem_uc", right_column="cod_uc"
        ),
        Relation(
            left_view="sem_faturamento_mensal",
            left_column="nope",
            right_view="sem_uc",
            right_column="cod_uc",
        ),
    ],
)
def test_relation_to_unknown_view_or_column_is_rejected(views, relation):
    with pytest.raises(ValidationError):
        SemanticLayer(version="v0", views=views, relations=(relation,))


def test_duplicate_view_names_are_rejected(views):
    with pytest.raises(ValidationError):
        SemanticLayer(version="v0", views=views + views[:1])


def test_column_units_map_each_column_to_its_unit_and_drop_ambiguous_names():
    def view(name, *columns):
        return ViewSpec(name=name, description="d", grain="g", columns=columns)

    def column(name, unit=None):
        return ColumnSpec(name=name, type="numeric", description="d", unit=unit)

    layer = SemanticLayer(
        version="1",
        views=(
            view(
                "sem_a", column("receita_faturada", "R$"), column("competencia"), column("x", "h")
            ),
            view("sem_b", column("receita_faturada", "R$"), column("x", "kWh")),
        ),
    )

    assert layer.column_units == {"receita_faturada": "R$"}
