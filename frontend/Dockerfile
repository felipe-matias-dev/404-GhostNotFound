# syntax=docker/dockerfile:1
# Servidor de desenvolvimento do Vite. No docker compose, o código é montado por cima e o
# Vite recarrega a página a cada mudança. Deploy em nuvem está fora do escopo (planejamento).
FROM node:22-slim

WORKDIR /app
RUN chown node:node /app
USER node

# Dependências antes do código: a camada só é refeita quando o package-lock.json muda.
COPY --chown=node:node package.json package-lock.json ./
RUN --mount=type=cache,target=/home/node/.npm,uid=1000,gid=1000 \
    npm ci --no-audit --no-fund

COPY --chown=node:node . .

EXPOSE 3000
# Pronto quando o Vite responde: `docker compose up --wait` só termina com o portal no ar.
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000').then((r) => process.exit(r.ok ? 0 : 1), () => process.exit(1))"]
# 0.0.0.0: dentro do container, localhost não é alcançável pela máquina.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
