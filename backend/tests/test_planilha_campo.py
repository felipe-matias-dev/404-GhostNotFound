from datetime import datetime
from io import BytesIO
from zipfile import ZipFile

import pytest
from openpyxl import Workbook

from venergy_api import planilha_campo
from venergy_api.ordens import ResultadoOrdem
from venergy_api.planilha_campo import PlanilhaInvalida, ler_planilha

CABECALHO = [
    "id_inspecao",
    "id_uc",
    "data",
    "inspetor",
    "resultado",
    "tipo_irregularidade",
    "kwh_recuperado",
]


def planilha(abas: dict[str, list[list]]) -> bytes:
    livro = Workbook()
    livro.remove(livro.active)
    for nome, linhas in abas.items():
        aba = livro.create_sheet(nome)
        for linha in linhas:
            aba.append(linha)
    saida = BytesIO()
    livro.save(saida)
    return saida.getvalue()


def uma_aba(*linhas: list, cabecalho: list = CABECALHO) -> bytes:
    return planilha({"ago-set": [cabecalho, *linhas]})


CONFIRMADA = [
    "INS-1",
    "0001",
    "2025-08-12",
    "Fulano",
    "IRREGULARIDADE CONFIRMADA",
    "DESVIO DIRETO",
    120.5,
]
SEM_IRREGULARIDADE = ["INS-2", "0002", "2025-08-13", "Ciclana", "SEM IRREGULARIDADE", None, 0]


def test_confirmed_irregularity_becomes_a_concluded_order_with_the_field_details() -> None:
    lida = ler_planilha(uma_aba(CONFIRMADA))

    assert lida.rejeitadas == []
    (linha,) = lida.validas
    assert (linha.aba, linha.linha, linha.cod_uc) == ("ago-set", 2, "0001")
    assert linha.resultado is ResultadoOrdem.IRREGULAR_CONFIRMADA
    assert linha.observacao == (
        "Planilha de campo: desvio direto, 120,5 kWh recuperados, inspetor Fulano, "
        "12/08/2025 (inspeção INS-1)"
    )


def test_no_irregularity_becomes_regular() -> None:
    (linha,) = ler_planilha(uma_aba(SEM_IRREGULARIDADE)).validas

    assert linha.resultado is ResultadoOrdem.REGULAR
    assert linha.observacao == (
        "Planilha de campo: sem irregularidade, inspetor Ciclana, 13/08/2025 (inspeção INS-2)"
    )


@pytest.mark.parametrize(
    ("escrito", "esperado"),
    [
        ("confirmada", ResultadoOrdem.IRREGULAR_CONFIRMADA),
        ("  Irregularidade   Confirmada ", ResultadoOrdem.IRREGULAR_CONFIRMADA),
        ("sem irregularidade", ResultadoOrdem.REGULAR),
        ("NADA CONSTA", ResultadoOrdem.REGULAR),
    ],
)
def test_result_spellings_are_normalized(escrito: str, esperado: ResultadoOrdem) -> None:
    tipo, kwh = ("BY-PASS", 10) if esperado is ResultadoOrdem.IRREGULAR_CONFIRMADA else (None, 0)

    (linha,) = ler_planilha(uma_aba(["INS-3", "0003", None, None, escrito, tipo, kwh])).validas

    assert linha.resultado is esperado


@pytest.mark.parametrize("ausente", ["", "-", "N/A", "null", None])
def test_absent_irregularity_type_is_any_of_the_known_spellings(ausente: str | None) -> None:
    lida = ler_planilha(uma_aba(["INS-4", "0004", None, None, "SEM IRREGULARIDADE", ausente, 0]))

    assert len(lida.validas) == 1


@pytest.mark.parametrize(
    "escrito",
    ["2025-08-12", "12.08.2025", "12/08/2025", "08-12-2025", datetime(2025, 8, 12, 9, 30)],
)
def test_the_four_date_formats_and_excel_dates_are_understood(escrito: object) -> None:
    (linha,) = ler_planilha(
        uma_aba(["INS-5", "0005", escrito, None, "SEM IRREGULARIDADE", None, 0])
    ).validas

    assert "12/08/2025" in linha.observacao


def test_kwh_with_decimal_comma_and_thousands_dot() -> None:
    (linha,) = ler_planilha(
        uma_aba(["INS-6", "0006", None, None, "CONFIRMADA", "BY-PASS", "1.234,5"])
    ).validas

    assert "1.234,5 kWh recuperados" in linha.observacao


def test_numeric_uc_cell_is_read_as_text() -> None:
    (linha,) = ler_planilha(
        uma_aba(["INS-7", 17, None, None, "SEM IRREGULARIDADE", None, 0])
    ).validas

    assert linha.cod_uc == "17"


@pytest.mark.parametrize(
    ("linha", "motivo"),
    [
        (["I", "0001", None, None, "FRAUDE", "BY-PASS", 5], "Resultado não reconhecido"),
        (["I", "0001", None, None, "CONFIRMADA", None, 5], "sem o tipo de irregularidade"),
        (["I", "0001", None, None, "CONFIRMADA", "BY-PASS", 0], "kWh recuperado maior que zero"),
        (["I", "0001", None, None, "CONFIRMADA", "BY-PASS", None], "kWh recuperado maior que zero"),
        (["I", "0001", None, None, "SEM IRREGULARIDADE", None, 7], "Sem irregularidade com kWh"),
        (
            ["I", "0001", None, None, "SEM IRREGULARIDADE", "BY-PASS", 0],
            "Sem irregularidade com tipo",
        ),
        (["I", "0001", None, None, "CONFIRMADA", "BY-PASS", "muito"], "kWh recuperado inválido"),
        (["I", "0001", "ontem", None, "SEM IRREGULARIDADE", None, 0], "Data inválida"),
        (["I", None, None, None, "SEM IRREGULARIDADE", None, 0], "UC em branco"),
        (["I", "0001", None, None, None, None, 0], "Resultado em branco"),
    ],
)
def test_incoherent_rows_are_rejected_with_the_reason(linha: list, motivo: str) -> None:
    lida = ler_planilha(uma_aba(linha))

    assert lida.validas == []
    (rejeitada,) = lida.rejeitadas
    assert motivo in rejeitada.motivo
    assert (rejeitada.aba, rejeitada.linha) == ("ago-set", 2)


def test_a_repeated_uc_keeps_only_the_first_row() -> None:
    lida = ler_planilha(uma_aba(CONFIRMADA, [*CONFIRMADA[:4], "SEM IRREGULARIDADE", None, 0]))

    assert [linha.linha for linha in lida.validas] == [2]
    (rejeitada,) = lida.rejeitadas
    assert rejeitada.linha == 3
    assert "repetida" in rejeitada.motivo


def test_an_invalid_first_row_does_not_block_a_later_valid_row_of_the_same_uc() -> None:
    lida = ler_planilha(uma_aba(["I", "0001", None, None, "FRAUDE", None, 0], CONFIRMADA))

    assert [linha.linha for linha in lida.validas] == [3]
    assert len(lida.rejeitadas) == 1


def test_every_sheet_is_read_and_counted_and_blank_rows_are_ignored() -> None:
    conteudo = planilha(
        {
            "ago-set": [CABECALHO, CONFIRMADA, [None] * 7],
            "dez": [CABECALHO, SEM_IRREGULARIDADE],
        }
    )

    lida = ler_planilha(conteudo)

    assert lida.linhas_lidas == 2
    assert [(linha.aba, linha.cod_uc) for linha in lida.validas] == [
        ("ago-set", "0001"),
        ("dez", "0002"),
    ]


def test_headers_ignore_case_and_spaces() -> None:
    cabecalho = [" ID_UC ", "Resultado", "Tipo Irregularidade", "KWH_Recuperado"]

    (linha,) = ler_planilha(
        uma_aba(["0009", "confirmada", "BY-PASS", 3], cabecalho=cabecalho)
    ).validas

    assert linha.cod_uc == "0009"


def test_optional_columns_may_be_missing() -> None:
    (linha,) = ler_planilha(
        uma_aba(["0009", "SEM IRREGULARIDADE"], cabecalho=["id_uc", "resultado"])
    ).validas

    assert linha.observacao == "Planilha de campo: sem irregularidade"


def test_a_file_that_is_not_xlsx_is_invalid() -> None:
    with pytest.raises(PlanilhaInvalida, match="XLSX"):
        ler_planilha(b"isto nao e uma planilha")


def test_missing_required_column_is_invalid_and_names_the_sheet() -> None:
    with pytest.raises(PlanilhaInvalida, match=r"ago-set.*id_uc"):
        ler_planilha(
            uma_aba(["INS-1", "SEM IRREGULARIDADE"], cabecalho=["id_inspecao", "resultado"])
        )


def test_a_workbook_without_rows_is_invalid() -> None:
    with pytest.raises(PlanilhaInvalida, match="vazia"):
        ler_planilha(planilha({"ago-set": [CABECALHO]}))


def test_a_file_over_the_size_limit_is_invalid() -> None:
    with pytest.raises(PlanilhaInvalida, match="grande"):
        ler_planilha(b"0" * (planilha_campo.MAX_BYTES + 1))


def test_more_rows_than_the_limit_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(planilha_campo, "MAX_LINHAS", 1)

    with pytest.raises(PlanilhaInvalida, match="linhas"):
        ler_planilha(uma_aba(CONFIRMADA, SEM_IRREGULARIDADE))


def test_a_very_long_note_is_cut_at_the_modal_limit() -> None:
    (linha,) = ler_planilha(
        uma_aba(["INS-8", "0008", None, "x" * 2000, "SEM IRREGULARIDADE", None, 0])
    ).validas

    assert len(linha.observacao) == planilha_campo.MAX_OBSERVACAO


def test_a_truncated_sheet_is_an_invalid_file_and_not_a_crash() -> None:
    original = ZipFile(BytesIO(uma_aba(CONFIRMADA)))
    saida = BytesIO()
    with ZipFile(saida, "w") as copia:
        for nome in original.namelist():
            dados = original.read(nome)
            copia.writestr(nome, dados[: len(dados) // 2] if "worksheets/" in nome else dados)

    with pytest.raises(PlanilhaInvalida):
        ler_planilha(saida.getvalue())


def test_too_many_blank_rows_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(planilha_campo, "MAX_LINHAS_EM_BRANCO", 2)

    with pytest.raises(PlanilhaInvalida, match="em branco"):
        ler_planilha(uma_aba([" "], [" "], [" "], CONFIRMADA))


@pytest.mark.parametrize(("escrito", "esperado"), [("1.234", "1.234 kWh"), (1.234, "1,234 kWh")])
def test_dot_is_a_thousands_separator_only_in_typed_text(escrito: object, esperado: str) -> None:
    linha = list(CONFIRMADA)
    linha[CABECALHO.index("kwh_recuperado")] = escrito

    assert esperado in ler_planilha(uma_aba(linha)).validas[0].observacao


def test_negative_kwh_is_rejected_even_without_irregularity() -> None:
    linha = ["INS-2", "0002", None, None, "SEM IRREGULARIDADE", None, -5]

    assert "negativo" in ler_planilha(uma_aba(linha)).rejeitadas[0].motivo
