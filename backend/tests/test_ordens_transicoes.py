import pytest

from venergy_api.ordens import TRANSICOES, StatusOrdem, TransicaoInvalidaError, validar_transicao

VALID_TRANSITIONS = [
    (StatusOrdem.GERADA, StatusOrdem.EM_CAMPO),
    (StatusOrdem.GERADA, StatusOrdem.CANCELADA),
    (StatusOrdem.EM_CAMPO, StatusOrdem.CONCLUIDA),
    (StatusOrdem.EM_CAMPO, StatusOrdem.CANCELADA),
]

# Todos os pares possíveis menos os válidos: uma transição nova no mapa sem teste
# correspondente faz este conjunto mudar e a suíte acusar.
INVALID_TRANSITIONS = [
    (atual, novo)
    for atual in StatusOrdem
    for novo in StatusOrdem
    if (atual, novo) not in VALID_TRANSITIONS
]


@pytest.mark.parametrize(("atual", "novo"), VALID_TRANSITIONS)
def test_allows_the_expected_transitions(atual: StatusOrdem, novo: StatusOrdem) -> None:
    validar_transicao(atual, novo)


@pytest.mark.parametrize(("atual", "novo"), INVALID_TRANSITIONS)
def test_rejects_every_other_transition(atual: StatusOrdem, novo: StatusOrdem) -> None:
    with pytest.raises(TransicaoInvalidaError):
        validar_transicao(atual, novo)


def test_every_status_has_an_entry_in_the_transition_map() -> None:
    assert set(TRANSICOES) == set(StatusOrdem)


def test_error_message_names_both_statuses() -> None:
    with pytest.raises(TransicaoInvalidaError, match="de CONCLUIDA para EM_CAMPO"):
        validar_transicao(StatusOrdem.CONCLUIDA, StatusOrdem.EM_CAMPO)
