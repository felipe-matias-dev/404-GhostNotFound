<!-- intent-skills:start -->
## Skill Loading

Use the repository’s installed Intent. If it is unavailable, report the missing dependency instead of downloading a replacement.
Before editing files for a substantial task:
- Run `npm exec --no -- intent list` from the workspace root to see available local skills.
- If a listed skill matches the task, run `npm exec --no -- intent load <package>#<skill>` before changing files.
- Use the loaded `SKILL.md` guidance while making the change.
- Monorepos: when working across packages, run the skill check from the workspace root and prefer the local skill for the package being changed.
- Multiple matches: prefer the most specific local skill for the package or concern you are changing; load additional skills only when the task spans multiple packages or concerns.
<!-- intent-skills:end -->

## Arquitetura do frontend

Arquitetura em camadas por feature (detalhes e exemplo em `README.md#arquitetura`). Não crie pastas vazias; crie conforme a necessidade.

```
src/
├── assets/                # imagens, ícones, fontes
├── components/layout/     # casca do app (sidebar, header)
├── components/ui/<nome>/  # <nome>.tsx + index.ts; genérico, sem regra de negócio
├── features/<feature>/    # components/ hooks/ pages/ api.ts conversions.ts types.ts index.ts
├── integrations/          # configuração de bibliotecas (TanStack Query)
├── lib/                   # infraestrutura genérica (api.ts, format.ts)
├── pages/                 # telas fora de feature (não encontrado, erro)
└── routes/                # rotas do TanStack Router
```

Regras:

- Dependências descem: `routes` → `features`/`pages` → `components` e `lib`. `components/ui` e `lib` nunca importam de `features`.
- `routes/` é fina: apenas `createFileRoute`, `validateSearch` (Zod) e `loader`; o `component` vem de `features/<feature>/pages` ou `pages/`.
- Páginas leem params/search com `getRouteApi("/rota")`; não importam o `Route` do arquivo de rota.
- Fora da feature, importe só pelo `index.ts` dela (`#/features/perdas`).
- `api.ts` da feature chama o client tipado `api` de `#/lib/api` com `unwrap` (`unwrap(api.GET("/rota/{id}", { params: { path: { id } } }))`); nunca `fetch` direto nem tipos de resposta escritos à mão: use `components["schemas"]` de `#/lib/api-schema.gen`. `conversions.ts` só tem funções puras (resposta da API → modelo da tela).
- Dados de servidor só via TanStack Query (hooks em `features/<feature>/hooks`); após mutation, invalide as queries afetadas.
- Filtros de tela ficam na URL (`validateSearch` com Zod 4, `.catch()` para padrão; sem `@tanstack/zod-adapter`).
- Valores exibidos (R$, kWh, %, competência, datas) sempre via `#/lib/format`.
- Nomes: features em camelCase (`unidadeConsumidora`); componentes de `ui/` em kebab-case (`number-input`). Imports absolutos com `#/`.
- Não edite `src/routeTree.gen.ts` nem `src/lib/api-schema.gen.ts`. Este é gerado de `contracts/openapi.json` por `npm run gen:api`; quando o backend muda uma rota, exporte o contrato e rode o `gen:api` (ver `README.md#client-da-api`). Não existe `App.tsx`: o shell é `src/routes/__root.tsx` + `src/router.tsx`.
- App é SPA (`tanstackStart({ spa: { enabled: true } })`); não use `createServerFn` nem server routes: o backend é o FastAPI.
- Design system no Storybook (`npm run storybook`, http://localhost:6006): todo componente de `components/ui/` e `components/layout/` tem `<nome>.stories.tsx` ao lado, com `title` em `Componentes/` ou `Layout/`, e estados padrão/carregando/erro/vazio. Estilo só por tokens do `@theme` em `src/styles.css`. Sem biblioteca de componentes como dependência: componentes do shadcn/ui (estilo `base-nova`, sobre Base UI; sem Radix) entram por `npx shadcn@latest add <nome>` (gera `src/components/ui/<nome>.tsx`; se a CLI instalar o pacote npm `cn`, remova: o `cn` é o de `#/lib/utils`), são movidos para `ui/<nome>/<nome>.tsx` + `index.ts` e têm as classes trocadas pelos tokens (sem `primary`/`ring`/`opacity` do shadcn); `cn` fica em `#/lib/utils` (com os tokens de `styles.css` registrados no tailwind-merge). O interior.dev segue como referência de micro-interação. Ícones só de `@phosphor-icons/react` (`TrashIcon`…), `aria-hidden`, cor por `currentColor` e tamanho por `size-*` (regras em Fundamentos/Ícones). Regras completas em `.storybook/docs/introducao.mdx`.
- Não há `engines/`. Testes: `npm test` (Vitest) só para funções puras com regra de tela, em `__tests__/` na feature, sem DOM; nada de testar biblioteca, wiring ou texto.

Features previstas: `visaoGeral`, `receita`, `unidadeConsumidora`, `perdas`, `operacao`, `agente`, `auth`.
