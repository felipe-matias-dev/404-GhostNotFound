# syntax=docker/dockerfile:1
# Imagem da API. No docker compose, o código de src/ é montado por cima e o uvicorn
# recarrega a cada mudança; sem o volume, a imagem roda sozinha com o código copiado.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /bin/uv

# A venv fica fora de /app para não ser escondida pelo volume do código no compose.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências antes do código: a camada só é refeita quando o uv.lock muda.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Sem root: o mesmo UID do primeiro usuário do Linux, dono dos arquivos montados.
RUN useradd --uid 1000 --create-home app
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["uvicorn", "venergy_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
