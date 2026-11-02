"""Formato dos eventos Server-Sent Events, compartilhado pelas rotas que transmitem em fluxo."""

# Comentário SSE: o navegador ignora, mas a linha mantém o proxy de pé e revela o cliente que saiu.
PING = ": ping\n\n"


def evento_sse(evento: str, dados: str) -> str:
    return f"event: {evento}\ndata: {dados}\n\n"
