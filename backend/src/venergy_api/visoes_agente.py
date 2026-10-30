"""Schema e views do agente: `semantic` é tudo o que o usuário venergy_agent enxerga (D1)."""

from pathlib import Path

from sqlalchemy import Connection, text

AGENT_VIEWS_SQL = Path(__file__).resolve().parents[3] / "ai-agent" / "semantic" / "views.sql"


def drop_agent_views(connection: Connection) -> None:
    """Apaga as views sem_* do agente, para as tabelas da Gold poderem ser recriadas."""
    # Pelo catálogo, e não pelos nomes do views.sql: uma view que o GenAI renomeou ou tirou
    # do arquivo ainda estaria presa à tabela, e o DROP da tabela falharia. O schema gold entra
    # porque as views moravam lá num banco antigo.
    linhas = connection.execute(
        text(
            r"SELECT schemaname, viewname FROM pg_views "
            r"WHERE schemaname IN ('gold', 'semantic') AND viewname LIKE 'sem\_%'"
        )
    ).all()
    if not linhas:
        return
    # Um DROP só, com todas: se uma view ler de outra, o Postgres resolve a ordem. Os nomes
    # vêm do catálogo, e não de entrada de usuário.
    quote = connection.dialect.identifier_preparer.quote
    nomes = ", ".join(f"{quote(schema)}.{quote(nome)}" for schema, nome in linhas)
    connection.execute(text(f"DROP VIEW {nomes}"))


def garantir_permissoes_do_agente(connection: Connection) -> None:
    """Deixa um banco antigo como o init cria um novo: o agente lê só o schema semantic.

    Só mexe em permissões e no schema das views: nunca apaga nem altera dado.
    """
    for comando in (
        "CREATE SCHEMA IF NOT EXISTS semantic",
        "GRANT USAGE ON SCHEMA semantic TO venergy_agent",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA semantic GRANT SELECT ON TABLES TO venergy_agent",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA gold REVOKE SELECT ON TABLES FROM venergy_agent",
        "REVOKE ALL ON ALL TABLES IN SCHEMA gold FROM venergy_agent",
        "REVOKE USAGE ON SCHEMA gold FROM venergy_agent",
        "ALTER ROLE venergy_agent SET statement_timeout = '30s'",
    ):
        connection.execute(text(comando))


def migrar_views_do_agente(connection: Connection) -> None:
    """Na subida, leva as views para semantic num banco já carregado, sem exigir nova carga."""
    garantir_permissoes_do_agente(connection)
    tem_gold = connection.scalar(text("SELECT to_regclass('gold.gold_dim_uc')")) is not None
    tem_views = connection.scalar(text("SELECT to_regclass('semantic.sem_uc')")) is not None
    if tem_gold and not tem_views and AGENT_VIEWS_SQL.exists():
        drop_agent_views(connection)
        connection.exec_driver_sql(AGENT_VIEWS_SQL.read_text(encoding="utf-8"))
