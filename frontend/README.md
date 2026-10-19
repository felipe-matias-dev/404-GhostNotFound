# Frontend — V-Energy Grid 360

Portal web do V-Energy Grid 360. SPA em React + TypeScript (Vite) que consome a API FastAPI do `backend/`.

## Stack

- **TanStack Start** em modo SPA (sem SSR) — roteamento por arquivos com TanStack Router
- **TanStack Query** (dados da API), **Table** (tabelas), **Form** (formulários)
- **Zod** (validação de filtros na URL e formulários)
- **Tailwind CSS** e **Biome** (lint + formatação)

## Como rodar

Requer Node 22.12+ (ou 20.19+).

```bash
npm install
cp .env.example .env.local   # ajuste se o backend não estiver em localhost:8000
npm run dev                  # http://localhost:3000
```

## Variáveis de ambiente

| Variável | Padrão | Uso |
|---|---|---|
| `VITE_API_URL` | `/api` | Base da API usada pelo navegador. Fora do dev, URL completa do FastAPI. |
| `API_PROXY_TARGET` | `http://localhost:8000` | Só em dev: o Vite encaminha `/api/*` para cá, sem o prefixo (`/api/ucs` → `/ucs`). |

## Scripts

| Comando | O que faz |
|---|---|
| `npm run dev` | Servidor de desenvolvimento |
| `npm run build` | Build de produção em `dist/client` |
| `npm run check` | Lint + formatação (Biome) |
| `npx tsc --noEmit` | Checagem de tipos |
| `npm run gen:api` | Regenera `src/lib/api-schema.gen.ts` a partir de `contracts/openapi.json` |

## Client da API

O contrato entre backend e frontend é o OpenAPI gerado pelo FastAPI, versionado em
[`contracts/openapi.json`](../contracts/openapi.json). Dele saem os tipos de
`src/lib/api-schema.gen.ts`, usados pelo client `api` de `src/lib/api.ts`
([openapi-fetch](https://openapi-ts.dev/openapi-fetch/)): rota, parâmetros e resposta
são checados na compilação.

```ts
// src/features/unidadeConsumidora/api.ts
import { api, unwrap } from "#/lib/api";
import type { components } from "#/lib/api-schema.gen";

export type DimUc = components["schemas"]["DimUcSchema"];

export function getUnidadeConsumidora(codUc: string): Promise<DimUc> {
	return unwrap(
		api.GET("/unidades-consumidoras/{cod_uc}", {
			params: { path: { cod_uc: codUc } },
		}),
	);
}
```

`unwrap` devolve o corpo da resposta ou lança `ApiError` (com `status` e o `body` do
erro), que o TanStack Query entrega em `error`.

Quando uma rota muda no backend:

```bash
cd backend && uv run python -m venergy_api.openapi   # atualiza contracts/openapi.json
cd ../frontend && npm run gen:api                    # atualiza os tipos
npx tsc --noEmit                                     # aponta as telas que quebraram
```

O hook de pre-commit e o CI rodam os dois geradores e falham se o resultado não estiver
commitado, então contrato e tipos nunca ficam desatualizados.

## Arquitetura

Arquitetura em camadas, organizada por feature. Pastas são criadas conforme a necessidade.

```
src/
├── assets/              # imagens, ícones, fontes
├── components/
│   ├── layout/          # casca do app: sidebar, header, containers de página
│   └── ui/<nome>/       # componentes genéricos, sem regra de negócio
│       ├── <nome>.tsx
│       └── index.ts
├── features/<feature>/  # uma pasta por área do negócio
│   ├── components/      # componentes da feature
│   ├── hooks/           # useQuery/useMutation da feature
│   ├── pages/           # telas da feature
│   ├── api.ts           # chamadas ao FastAPI (client `api` + `unwrap`) e query keys
│   ├── conversions.ts   # resposta da API → modelo da tela (funções puras)
│   ├── types.ts         # tipos da feature
│   └── index.ts         # API pública da feature
├── integrations/        # configuração de bibliotecas (TanStack Query)
├── lib/                 # infraestrutura genérica: api.ts, format.ts
├── pages/               # telas fora de feature (não encontrado, erro)
├── routes/              # rotas do TanStack Router (arquivo → URL)
└── router.tsx           # criação do router
```

`src/routeTree.gen.ts` é gerado automaticamente pelo `npm run dev`/`build` — não edite.

### Regras das camadas

- **Dependências descem**: `routes` → `features`/`pages` → `components` e `lib`. `components/ui` e `lib` nunca importam de `features`.
- **`routes/` é fina**: só `createFileRoute`, `validateSearch` (Zod) e `loader`; o componente vem de `features/<feature>/pages` ou `pages/`.
- **Páginas leem params/search** com `getRouteApi("/rota")`, sem importar o `Route` do arquivo de rota.
- **Fora da feature, importe só pelo `index.ts`** dela (`#/features/perdas`), nunca de arquivos internos.
- **Nomes**: features em camelCase (`unidadeConsumidora`), componentes de `ui/` em kebab-case (`number-input`).
- **Imports** absolutos com `#/` (`#/lib/api`).

Exemplo de rota:

```tsx
// src/routes/perdas.tsx
import { createFileRoute } from "@tanstack/react-router";
import { FilaInspecaoPage, filaSearchSchema } from "#/features/perdas";

export const Route = createFileRoute("/perdas")({
	validateSearch: filaSearchSchema,
	component: FilaInspecaoPage,
});
```

### Features previstas

`visaoGeral` (KPIs), `receita` (preço × volume), `unidadeConsumidora` (visão 360), `perdas` (fila e ordens de inspeção), `operacao` (DEC/FEC), `agente` (chat e insights de IA), `auth` (perfis, quando entrar).

## Convenções

- Dados da API: hooks com `useQuery`/`useMutation` chamando o `api.ts` da feature; após mutations, invalide as queries afetadas.
- Filtros de tela ficam na URL via `validateSearch` com Zod.
- Números e datas exibidos sempre via `src/lib/format.ts`.
- Testes e Storybook ainda não estão configurados. Quando entrarem: `__tests__/` dentro da feature e `<nome>.stories.tsx` ao lado do componente em `ui/`.
