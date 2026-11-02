import pytest

from venergy_api.ordens import SEGUNDOS_POR_DIA, LimitesDeAtraso, StatusOrdem, esta_atrasada

LIMITES = LimitesDeAtraso(gerada_dias=5, em_campo_dias=10)


@pytest.mark.parametrize(
    ("status", "limite_dias"),
    [(StatusOrdem.GERADA, 5), (StatusOrdem.EM_CAMPO, 10)],
)
def test_order_is_late_only_after_the_limit_of_its_status(
    status: StatusOrdem, limite_dias: int
) -> None:
    assert not esta_atrasada(status, limite_dias * SEGUNDOS_POR_DIA, LIMITES)
    assert esta_atrasada(status, limite_dias * SEGUNDOS_POR_DIA + 1, LIMITES)


def test_each_status_has_its_own_limit() -> None:
    seis_dias = 6 * SEGUNDOS_POR_DIA

    assert esta_atrasada(StatusOrdem.GERADA, seis_dias, LIMITES)
    assert not esta_atrasada(StatusOrdem.EM_CAMPO, seis_dias, LIMITES)


@pytest.mark.parametrize("status", [StatusOrdem.CONCLUIDA, StatusOrdem.CANCELADA])
def test_finished_order_is_never_late(status: StatusOrdem) -> None:
    assert not esta_atrasada(status, 365 * SEGUNDOS_POR_DIA, LIMITES)


def test_zero_days_makes_any_wait_late_but_not_the_instant_of_the_change() -> None:
    sem_tolerancia = LimitesDeAtraso(gerada_dias=0, em_campo_dias=0)

    assert not esta_atrasada(StatusOrdem.GERADA, 0, sem_tolerancia)
    assert esta_atrasada(StatusOrdem.GERADA, 1, sem_tolerancia)
