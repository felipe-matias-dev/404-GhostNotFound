"""Conversas do agente por usuário: os turnos vêm da auditoria e o resto de app.ai_sessao."""

from collections import defaultdict
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from venergy_api.auditoria import sessao_de_outro_usuario
from venergy_api.models import AiAuditoria, AiSessao
from venergy_api.schemas import AuditoriaIaSchema, SessaoIaSchema

MAX_SESSOES = 50
MAX_TITULO_PADRAO = 80


def sessao_excluida(session: Session, session_id: str) -> bool:
    return bool(
        session.scalar(
            select(
                exists().where(
                    AiSessao.session_id == session_id,
                    AiSessao.excluido_em.is_not(None),
                )
            )
        )
    )


def sessao_disponivel(session: Session, session_id: str, usuario: str) -> bool:
    """Se a conversa tem turnos, é só do usuário e não foi excluída."""
    tem_turnos = session.scalar(select(exists().where(AiAuditoria.session_id == session_id)))
    return bool(
        tem_turnos
        and not sessao_de_outro_usuario(session, session_id, usuario)
        and not sessao_excluida(session, session_id)
    )


def listar_sessoes(
    session: Session, usuario: str, session_id: str | None = None
) -> list[SessaoIaSchema]:
    turnos_por_sessao = (
        select(
            AiAuditoria.session_id,
            func.min(AiAuditoria.criado_em).label("criada_em"),
            func.max(AiAuditoria.criado_em).label("atualizada_em"),
        )
        .where(AiAuditoria.usuario == usuario)
        .group_by(AiAuditoria.session_id)
        .subquery()
    )
    favorita = func.coalesce(AiSessao.favorita, False)
    consulta = (
        select(
            turnos_por_sessao.c.session_id,
            turnos_por_sessao.c.criada_em,
            turnos_por_sessao.c.atualizada_em,
            AiSessao.titulo,
            favorita.label("favorita"),
        )
        .outerjoin(AiSessao, AiSessao.session_id == turnos_por_sessao.c.session_id)
        .where(AiSessao.excluido_em.is_(None))
        .order_by(favorita.desc(), turnos_por_sessao.c.atualizada_em.desc())
        .limit(MAX_SESSOES)
    )
    if session_id is not None:
        consulta = consulta.where(turnos_por_sessao.c.session_id == session_id)
    cabecalhos = session.execute(consulta).all()

    turnos: dict[str, list[AiAuditoria]] = defaultdict(list)
    for auditoria in session.scalars(
        select(AiAuditoria)
        .where(
            AiAuditoria.usuario == usuario,
            AiAuditoria.session_id.in_([linha.session_id for linha in cabecalhos]),
        )
        .order_by(AiAuditoria.id)
    ):
        turnos[auditoria.session_id].append(auditoria)

    return [
        SessaoIaSchema(
            session_id=linha.session_id,
            titulo=linha.titulo or turnos[linha.session_id][0].pergunta[:MAX_TITULO_PADRAO],
            favorita=linha.favorita,
            criada_em=linha.criada_em,
            atualizada_em=linha.atualizada_em,
            turnos=[AuditoriaIaSchema.model_validate(t) for t in turnos[linha.session_id]],
        )
        for linha in cabecalhos
    ]


def _gravar(session: Session, session_id: str, usuario: str, valores: dict[str, Any]) -> None:
    session.execute(
        insert(AiSessao)
        .values(session_id=session_id, usuario=usuario, **valores)
        .on_conflict_do_update(
            index_elements=[AiSessao.session_id],
            set_={**valores, "atualizado_em": func.now()},
        )
    )
    session.commit()


def alterar_sessao(
    session: Session, session_id: str, usuario: str, valores: dict[str, Any]
) -> None:
    _gravar(session, session_id, usuario, valores)


def excluir_sessao(session: Session, session_id: str, usuario: str) -> None:
    _gravar(session, session_id, usuario, {"excluido_em": func.now()})
