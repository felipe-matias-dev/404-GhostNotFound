"""Colunas que o schema app ganhou depois que as tabelas já existiam.

Não há migrações, e o create_all só cria a tabela que falta: não acrescenta coluna a uma que já
existe. Apagar uma tabela do app para isso perderia as ordens de inspeção de quem já usa o portal
(DEC-050). Tudo aqui só acrescenta, com IF NOT EXISTS: nunca apaga nem altera dado.
"""

from sqlalchemy import Connection, text


def garantir_estrutura_do_app(connection: Connection) -> None:
    """Acrescenta ao schema app as colunas que faltam num banco criado antes delas."""
    # Num banco novo, a coluna já veio do create_all e o comando não faz nada.
    connection.execute(
        text("ALTER TABLE app.ordem_evento ADD COLUMN IF NOT EXISTS autor_login text")
    )
