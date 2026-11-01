"""Limite de tentativas de login por login e endereço (DEC-065).

Cinco senhas erradas seguidas do mesmo login, a partir do mesmo endereço e dentro da janela,
bloqueiam esse par até a falha mais antiga sair da janela. O bloqueio é por par, e não só por
login: do contrário, qualquer pessoa trancaria a conta do gerente de perdas de propósito.
"""

from datetime import timedelta
from math import ceil

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from venergy_api.models import TentativaLogin

ENDERECO_DESCONHECIDO = "desconhecido"


def travar_par(session: Session, login: str, ip: str) -> None:
    """Serializa as tentativas do mesmo par até o fim da transação.

    Sem a trava, 20 pedidos simultâneos leriam todos "0 falhas" e passariam do limite. O
    advisory lock vale entre processos da API (um asyncio.Lock não valeria) e é solto sozinho
    no commit ou no rollback. Duas chaves que colidem no hash só esperam uma pela outra.
    """
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:chave))"), {"chave": f"{login}|{ip}"}
    )


def segundos_de_bloqueio(
    session: Session, login: str, ip: str, max_falhas: int, janela_segundos: int
) -> int | None:
    """Quantos segundos faltam para o par poder tentar de novo, ou None se não está bloqueado.

    Contam as falhas da janela posteriores ao último sucesso: entrar certo zera a contagem. O
    relógio é o do banco, o mesmo que grava a tentativa. Bloqueado, a espera vai até a falha
    que deixa o total abaixo do limite sair da janela.
    """
    par = (TentativaLogin.login == login, TentativaLogin.ip == ip)
    ultimo_sucesso = (
        select(func.max(TentativaLogin.ocorrida_em))
        .where(*par, TentativaLogin.sucesso.is_(True))
        .scalar_subquery()
    )
    # Da mais antiga para a mais nova, ou seja, da maior idade para a menor.
    idades = [
        float(idade)
        for idade in session.scalars(
            select(func.extract("epoch", func.now() - TentativaLogin.ocorrida_em))
            .where(
                *par,
                TentativaLogin.sucesso.is_(False),
                TentativaLogin.ocorrida_em > func.now() - timedelta(seconds=janela_segundos),
                or_(ultimo_sucesso.is_(None), TentativaLogin.ocorrida_em > ultimo_sucesso),
            )
            .order_by(TentativaLogin.ocorrida_em)
        )
    ]
    if len(idades) < max_falhas:
        return None
    idade_da_que_libera = idades[len(idades) - max_falhas]
    return max(1, ceil(janela_segundos - idade_da_que_libera))


def registrar_tentativa(session: Session, login: str, ip: str, *, sucesso: bool) -> None:
    session.add(TentativaLogin(login=login, ip=ip, sucesso=sucesso))
