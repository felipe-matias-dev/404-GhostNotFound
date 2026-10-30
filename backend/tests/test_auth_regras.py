"""Regras de autenticação sem rota nem banco: token de sessão e hash de senha."""

from datetime import UTC, datetime, timedelta

import jwt

from venergy_api.auth import (
    Perfil,
    UsuarioLogado,
    conferir_senha,
    criar_token,
    gerar_hash,
    ler_token,
)

SEGREDO = "segredo-de-teste-com-tamanho-suficiente-para-hs256"

RAFAEL = UsuarioLogado(login="rafael", nome="Rafael", perfil=Perfil.PERDAS)


def test_token_devolve_o_mesmo_usuario():
    token = criar_token(RAFAEL, SEGREDO, agora=datetime.now(UTC))

    assert ler_token(token, SEGREDO) == RAFAEL


def test_token_vence_em_oito_horas():
    agora = datetime.now(UTC)

    dentro = criar_token(RAFAEL, SEGREDO, agora=agora - timedelta(hours=7, minutes=59))
    fora = criar_token(RAFAEL, SEGREDO, agora=agora - timedelta(hours=8, minutes=1))

    assert ler_token(dentro, SEGREDO) == RAFAEL
    assert ler_token(fora, SEGREDO) is None


def test_token_assinado_com_outro_segredo_e_recusado():
    token = criar_token(
        RAFAEL, "outro-segredo-tambem-com-tamanho-suficiente", agora=datetime.now(UTC)
    )

    assert ler_token(token, SEGREDO) is None


def test_token_sem_assinatura_e_recusado():
    # O ataque clássico: trocar o algoritmo para "none" e apresentar um perfil à escolha.
    carga = {
        "sub": "rafael",
        "nome": "Rafael",
        "perfil": "ti",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(carga, key="", algorithm="none")

    assert ler_token(token, SEGREDO) is None


def test_token_com_perfil_desconhecido_e_recusado():
    carga = {
        "sub": "rafael",
        "nome": "Rafael",
        "perfil": "admin",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(carga, SEGREDO, algorithm="HS256")

    assert ler_token(token, SEGREDO) is None


def test_texto_qualquer_nao_e_token():
    assert ler_token("isto-nao-e-um-token", SEGREDO) is None


def test_hash_confere_a_senha_certa_e_recusa_a_errada():
    hash_da_senha = gerar_hash("senha-de-demonstracao")

    assert conferir_senha("senha-de-demonstracao", hash_da_senha)
    assert not conferir_senha("outra-senha", hash_da_senha)


def test_hash_nao_guarda_a_senha_e_muda_a_cada_geracao():
    primeiro = gerar_hash("senha-de-demonstracao")
    segundo = gerar_hash("senha-de-demonstracao")

    assert "senha-de-demonstracao" not in primeiro
    assert primeiro != segundo
