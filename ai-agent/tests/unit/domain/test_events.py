import pytest

from venergy_agent.domain.events import Stage, StageEvent


@pytest.mark.parametrize(
    ("stage", "label"),
    [
        (Stage.UNDERSTANDING, "Entendendo a pergunta"),
        (Stage.QUERYING, "Consultando os dados"),
        (Stage.CORRECTING, "Ajustando a consulta"),
        (Stage.WRITING, "Escrevendo a resposta"),
    ],
)
def test_each_stage_has_its_portuguese_label(stage, label):
    assert StageEvent(stage=stage, attempt=1).label == label


def test_stage_event_serializes_without_technical_fields():
    event = StageEvent(stage=Stage.QUERYING, attempt=2)

    assert set(event.model_dump()) == {"type", "stage", "label", "attempt"}
