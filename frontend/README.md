# Frontend — V-Energy Grid 360

Portal web do V-Energy Grid 360. SPA em React + TypeScript (Vite) que consome a API FastAPI do `backend/`.

## Stack

- **TanStack Start** em modo SPA (sem SSR) — roteamento por arquivos com TanStack Router
- **TanStack Query** (dados da API), **Table** (tabelas), **Form** (formulários)
- **Zod** (validação de filtros na URL e formulários)
- **Tailwind CSS** e **Biome** (lint + formatação)
- **Storybook** (catálogo do design system)

## Como rodar

Com Docker, `docker compose up` na raiz sobe banco, API e este frontend em
http://localhost:3000: ver o [README da raiz](../README.md#como-executar-localmente).
`src/` é montado no container e recarrega a cada mudança.

Direto na máquina, requer Node 22.12+ (ou 20.19+) e a API no ar:

```bash
npm ci                       # versões exatas do package-lock.json
cp .env.example .env.local   # ajuste se o backend não estiver em localhost:8000
npm run dev                  # http://localhost:3000
```

### Login e perfis

O portal abre em `/login` quando não há sessão. A feature `auth` usa o contrato do
FastAPI (`/auth/login`, `/auth/me`, `/auth/logout`), via proxy `/api` e cookie
`HttpOnly`; nenhum token é guardado pelo JavaScript. Crie os usuários pelo comando
`make users` na raiz e use a senha `SENHA_DEMO` do seu `.env` (ver o README da raiz).
Não há cadastro público, recuperação de senha ou login social no backend.

| Perfil | Entrada | Minha área | Outras consultas |
|---|---|---|---|
| Diretoria | Visão geral | Visão geral, Receita, Rede, Consulta de UC | Perdas |
| Atendimento | Consulta de UC | Consulta de UC | Visão geral, Receita, Rede, Perdas |
| Perdas | Perdas | Consulta de UC, Perdas | Visão geral, Receita, Rede |
| Operação | Rede | Rede, Consulta de UC | Visão geral, Receita, Perdas |
| TI | Visão geral | Todas as telas existentes | Não aparece, pois todas estão em Minha área |

Todos os perfis encontram todas as telas existentes na sidebar, sem duplicações:
**Minha área** vem primeiro e **Outras consultas** reúne as demais telas. Grupos
vazios não aparecem. `PROFILES.primaryRoutes` define prioridade, não permissão.
O menu dá foco, não restringe leituras (DEC-049). Só Perdas vê a geração e as
ações das ordens; os demais consultam a tabela e o histórico, que mostra quem fez
cada mudança ([DEC-050](../docs/decisoes.md#dec-050--autoria-nos-eventos-das-ordens-de-inspeção)).
Um link de dados aberto sem sessão é retomado após o login. Retornos externos,
desconhecidos ou para o próprio login são descartados. Um `401` durante o uso
volta à entrada; `403` não encerra a sessão. Falha ao verificar a sessão mostra
uma opção de tentar novamente, sem confundir indisponibilidade com credencial inválida.
Sair ou trocar de usuário limpa as consultas em memória; as UCs recentes ficam
separadas por login no navegador, sem migrar o histórico compartilhado anterior.

O chat mostra as etapas recebidas de `POST /ai/ask/stream` e só exibe a resposta
completa no evento final. Minimizar ou fechar o widget só esconde a janela: a consulta
continua, com o indicador no botão flutuante, e a resposta fica disponível ao reabrir.
Durante a consulta é possível escrever a próxima pergunta, mas novos envios, sugestões
e tentativas de repetição não substituem a consulta ativa. O botão **Parar** cancela
explicitamente e preserva o rascunho. Também cancelam: sair da página `/agente`, criar
ou trocar de conversa, remover a conversa em andamento, limpar o histórico e sair do
portal. Perguntas canceladas podem ser tentadas novamente; o abandono conta no limite
de perguntas e os tokens já informados pelo provedor contam no orçamento (DEC-055).
Quando o agente pede esclarecimento, o chat exibe a pergunta uma única vez,
como parte do texto da resposta.
Falhas de interpretação do stream mostram uma mensagem de erro com opção de tentar
novamente, sem expor o erro técnico do parser. Uma resposta sem a linha vazia final
do evento SSE é incompleta: não é exibida como resposta concluída.

### Filtros das análises

Visão geral, Receita, Rede e Perdas compartilham período, município, bairro e classe
pela URL. Os filtros próprios de cada tela são lembrados enquanto a sessão do portal
estiver aberta; atualizar a página preserva apenas os filtros presentes na URL.
O botão de calendário abre a seleção de períodos nas telas analíticas, exceto Perdas.
A faixa superior reúne o recorte compartilhado; **Filtros de suspeitas** afeta apenas
os sinais da fila.
Na Rede, `inicio` e `fim` representam o período atual. Um par válido que não conste
na decomposição permanece selecionado, com aviso de indisponibilidade da ponte.
Com recorte, a Rede mostra localidades sem salvar essa visão como preferência; ao limpar
o recorte, volta ao ranking de alimentadores, salvo se localidades foi escolhida na URL.
Períodos inválidos recebidos por URL são removidos antes das consultas, com aviso visível.
A base deve terminar antes do início do período atual. Na URL, uma base sobreposta é
substituída pela sugestão e gera aviso; no seletor manual, a aplicação é bloqueada.
Para períodos maiores que 12 meses, a sugestão tem a mesma duração e termina no mês
anterior ao início do período atual.
Em Perdas, município, bairro e classe filtram fila e ordens, mas o período é só
contexto: a fila usa a janela fixa da Gold e as ordens não são filtradas por data.
Na consulta individual de UC, o histórico e as dívidas não são limitados pelo recorte.

A entrada reaproveita `Logo`, `Button`, `FloatingLabelInput` e os tokens de
`src/styles.css`, inclusive o tema salvo. A marca sobe antes de revelar o formulário;
o fundo em Canvas 2D representa conexões de distribuição e UCs, não dados ao vivo.
Não usa biblioteca 3D nem recursos externos. A animação pode ser pausada, para
quando a aba fica oculta e é estática com `prefers-reduced-motion: reduce`.


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
| `npm test` | Testes (Vitest) das funções puras em `src/**/__tests__/*.test.ts` |
| `npm run gen:api` | Regenera `src/lib/api-schema.gen.ts` a partir de `contracts/openapi.json` |
| `npm run gen:mapa -- <municípios> <bairros>` | Regenera `src/components/ui/region-map/rmr.gen.ts` e `rmr-bairros.gen.ts` (mapa da RMR) a partir das malhas do IBGE: [municípios](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais) (`PE_Municipios_AAAA`) e [bairros do Censo 2022](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/malha_com_atributos/bairros/shp/UF/PE/) (`PE_bairros_CD2022`); ver DEC-025 |
| `npm run storybook` | Storybook do design system em http://localhost:6006 |
| `npm run build-storybook` | Build estático do Storybook em `storybook-static/` |

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

### Casca do app

`src/routes/__root.tsx` envolve todas as rotas no `AppShell` (`components/layout/app-shell`), montado sobre a Sidebar do shadcn (`components/ui/sidebar`, variante `inset`): a navegação recolhe para ícones pelo trigger, pelo rail ou com Ctrl/Cmd+B. Com a navegação aberta, o trigger fica ao lado da logo; recolhida, ele passa para o header. Abaixo de 768px a navegação vira um `Sheet` e o trigger fica sempre no header. O header traz o título da seção (o `<h1>` da página) e o painel de conteúdo rola sozinho e volta ao topo a cada tela. Rota sem match cai em `pages/nao-encontrado.tsx`, sem título no header nem item ativo na navegação.

Tela nova na navegação: crie a rota e adicione o item em `NAVEGACAO` (`components/layout/app-sidebar/navegacao.ts`), com o ícone de **Fundamentos/Ícones**. Atualize `PROFILES.primaryRoutes` (`features/auth/profiles.ts`) para os cargos que a têm como prioridade. `organizarNavegacao` põe essas telas em **Minha área** e todas as demais em **Outras consultas**, sem exclusão nem duplicação. O título do header e o item ativo da sidebar vêm de `useItemAtivo`; rotas filhas que existem (`/uc/$id`) herdam a seção. **Consulta de UC** é uma ação que abre a palette, não um link para uma página de busca. O conteúdo da página vai dentro de `Pagina` (`components/layout/pagina`), que fixa largura e respiro.

Recorte da tela no topo (ex.: `Receita › Recife ▾ › Boa Viagem ▾`): a página renderiza `<HeaderTrilha>` (`components/layout/header`) com um `Breadcrumb`, e o conteúdo aparece no header logo depois do título, que vira link para a seção sem recorte. Na Receita, cada nível é um `DropdownMenu` para trocar de município ou bairro: é a forma acessível de escolher o que o mapa também escolhe.

### Features previstas

`visaoGeral` (KPIs), `receita` (preço × volume), `unidadeConsumidora` (visão 360), `perdas` (fila e ordens de inspeção), `operacao` (DEC/FEC), `agente` (chat e insights de IA), `auth` (perfis, quando entrar).

Insight de IA de uma tela (DEC-069): `InsightIa` (`#/features/agente`) vai ao lado da frase de leitura do gráfico que ele narra; na Receita, pelo `summaryAction` da ponte (`WaterfallChart`), com o hook `useInsightReceita`. O modelo só é chamado no clique em "Gerar insight" (a query tem `enabled: false` e o clique faz `refetch`); o texto abre numa caixa e o botão vira "Insight feito por IA". Se o provedor falhar, o texto for recusado ou a IA estiver desligada, a API manda a leitura da regra, e a caixa mostra "Leitura automática" (DEC-066). Sem texto ou com erro da rota, aparece "Insight indisponível." com "Tentar de novo".

### Visão 360 da unidade consumidora

- **Consulta de UC** na sidebar abre a palette global, também disponível por Ctrl/Cmd + K.
  A navegação se divide em **Minha área** e **Outras consultas**, conforme as prioridades do cargo, mantendo todas as telas acessíveis.
- A palette consulta `GET /unidades-consumidoras/{cod_uc}/visao-360` antes de navegar para
  `/uc?cod_uc=...`. A resposta preenche o cache da visão 360, sem uma segunda consulta.
  O código continua textual e exato; filtrar recentes não é busca global nem resolução aproximada de identidade.
- Os cinco códigos consultados com sucesso mais recentemente ficam em `localStorage`
  (`venergy:ucs-recentes`), sem nomes ou dados financeiros. Reconsulta move o código ao topo.
  **Limpar recentes** apaga a lista. Armazenamento bloqueado mantém a sessão funcional e informa a limitação.
- Setas, Home/End e Enter selecionam/consultam; Esc fecha e o modal restaura o foco.
  Alterar o texto ou fechar cancela o pedido pendente; 404 e falha técnica não navegam nem entram nos recentes.
  Avisos usam os tokens `danger` e `danger-subtle` (texto, borda e fundo), mantendo mensagem explícita e retry neutro.
- Links diretos continuam funcionando. `/uc` sem código só oferece **Buscar UC**; uma UC aberta
  oferece **Trocar UC** e **Atualizar dados**. A página não conserva um segundo formulário de busca.
- O provider da feature é montado na rota raiz; o shell recebe apenas o callback de abertura,
  sem importar a feature. Sem código não há consulta automática; troca de UC não reaproveita dados da anterior.
- O único tipo agregado é `Uc360Schema` do OpenAPI (alias `Uc360`); não há contrato antigo nem
  adaptador. `consumo.meses` alimenta o `TrendChart`; `null` interrompe a linha e zero permanece.
  A referência é `consumo.referencia`, global à Gold. `tendencia` e os dois percentuais vêm
  prontos do backend; estável significa faixa inclusiva de ±10%, não ausência de aumento.
  A variação de 12 meses informa `meses_comparados` e considera somente pares com fatura.
- A conta do ano anterior, o tipo de leitura e a diferença absoluta em kWh foram removidos:
  não existem no contrato aprovado. Valor, dias e bandeira exibidos são só do mês de referência.
  Não há cálculo de negócio nem chamadas em cascata para reconstruir os campos antigos.
- `faturas_nao_pagas.itens`, interrupções e `atendimentos` usam `DataTable`, cinco linhas por página.
  Cadastro, equipamento e GD ficam visíveis sem abas. Só dados mascarados identificam o titular.
- Refetch mantém os dados da mesma UC; uma falha os identifica como anteriores e oferece
  repetição. 404 é distinto de falha técnica. Não há operação de pagamento nem abertura de chamado.
- DS VE-360 preservado: grid operacional de duas colunas no desktop, uma no mobile,
  tabelas responsivas em cards e motion somente dos componentes internos (V3 M2 D8).
### Visão geral da diretoria

- Resumo de 12 meses e faixa mensal: valores e variações de `GET /indicadores/comparacao`.
- Tesoura: somas de `GET /indicadores/janelas?meses=12`, sem acumulação no frontend. A primeira
  e a última janelas completas sem sobreposição definem o par do resumo; o gráfico só converte
  as somas em variação sobre a primeira janela.
- Competências das janelas vêm da empresa inteira: um mês sem linha no recorte vale zero,
  enquanto uma lacuna global continua invalidando a janela.
- O link do resumo para a ponte só aparece se o mesmo par existir em
  `GET /receita/decomposicao/periodos`, sem fallback silencioso para outro período.
- `GET /receita/mensal` permanece para as competências do seletor mensal e as sparklines.
  DEC, FEC e satisfação da comparação são calculados no backend, não pela série mensal.
- Comparação mensal, resumo e série de janelas têm estados de erro e repetição independentes.

### Rede (DEC/FEC)

- Rota fina `/rede` com `validateSearch: redeSearchSchema`; a página lê search e navegação por `getRouteApi("/rede")`. Campos opcionais (`inicio`, `fim`, `criterio`, `visao`, `municipio`, `bairro`, `alimentador`, `serie`) viram estado efetivo sem duplicar defaults na URL.
- O conteúdo da Rede ocupa toda a largura disponível (`Pagina` com `max-w-none`), preservando o respiro lateral e a adaptação nativa da tabela em telas estreitas.
- A URL bruta é comparada com a forma canônica: bairro órfão, série sem alimentador, mês inválido e geografia sob `visao=alimentadores` são removidos uma vez com `replace`. Período incompleto ou invertido volta ao padrão resolvido pelo calendário (`useCompetencias` de `visaoGeral`, mesma chave `["visaoGeral","mensal"]`), e uma URL válida completa prevalece mesmo fora do calendário. Sem competências e sem URL, a tabela não consulta e o seletor manual fica habilitado.
- Padrão sem URL: últimos 12 meses de calendário até a competência mais recente, limitados à mais antiga da base. O calendário e a tabela têm estados de falha/vazio independentes; intervalo explícito continua consultando com calendário indisponível.
- Toolbar compacta: visão `Alimentadores | Localidades`, intervalo em popover com dois meses nativos (`De`/`Até`, `Aplicar`, `Últimos 12 meses`, mensagens de validação próprias e `aria-invalid`) e critério `DEC | FEC`. Trocar período, visão ou recorte limpa o painel; trocar o critério não fecha o painel nem troca a métrica dele. A paginação nativa de 10 linhas reinicia por `resetKey` (visão, período, critério, município, bairro) e nunca por `alimentador`/`serie`.
- Alimentadores usam o ranking global (`GET /continuidade/alimentadores/ranking`); Localidades começa nos municípios e desce para bairros e alimentadores por `GET /continuidade/recortes`. O nível exibido e as ações da linha vêm de `response.nivel`, nunca de uma resposta anterior; o título contextual deriva do recorte na URL. A ordem é a da API.
- Tabela: identificador do nível, DEC (`formatHoras`), FEC (`formatIndice`) e UCs (`formatNumero`); o cabeçalho do critério ativo ganha ênfase tipográfica. Sem números coloridos como alerta. `n_meses` aparece na legenda com singular.
- Painel do alimentador: Sheet à direita, aberto só por clique/teclado na linha ou deep link `alimentador`. Título `Alimentador {codigo}`, descrição do histórico global, aviso quando veio de bairro e período formatado. Um `TrendChart` de 300px, uma métrica por vez (`serie ?? criterio ?? "dec"`), série global pedida com `cod_alimentador` explícito, meses ausentes como `null`, zero como zero; o toggle não consulta nem reordena a tabela. O gráfico aceita até 120 meses; para períodos maiores, pede a redução do intervalo sem alterar a consulta. Fechar remove só `alimentador`/`serie`, preservando tabela, recorte, período e página e criando uma entrada no histórico ([DEC-045](../docs/decisoes.md)).
- Consultas: hooks em ordem fixa com `skipToken` para a visão inativa e para série sem código; `AbortSignal` propagado às três chamadas; cache global de 5 min sem `keepPreviousData`. Troca de chave mostra o molde nativo; recarga da mesma chave mantém os dados com `aria-busy`/`Atualizando…` e erro de refetch em aviso externo com retry, sem esconder as linhas. Erro inicial aparece no estado nativo, nunca como vazio.
- Acessibilidade: foco retorna à linha que abriu o painel (ou ao título `tabIndex={-1}` em deep link), `Sheet` prende o foco e `Esc`/X/backdrop fecham; Back/Forward reabrem pelo histórico. O gráfico expõe a tabela `sr-only` com todas as competências, inclusive as lacunas.

### Perdas

- O seletor superior em pills **Suspeitas / Inspeções** alterna as duas telas sem repetir os títulos do cabeçalho; a troca preserva a página e a seleção da fila. A fila usa `DataTable` com 20 UCs por página da API, inicialmente na ordem da Gold. A barra junto à lista mostra o total ou a seleção atual e a ação **Gerar ordens de inspeção**. A energia estimada e a presença de ordem ativa podem ser ordenadas na API, antes da paginação; mudar a ordem retorna à primeira página e limpa a seleção. UCs com OI ativa não são selecionáveis. Abrir a linha mostra os motivos completos; clicar no código da UC abre sua consulta.
- Os códigos de UC têm sublinhado permanente para identificar os links; o traço fica dentro da altura da célula, sem ser cortado pela truncagem do texto.
- A fila combina filtros antes da paginação. Leituras estimadas aceitam faixas de 25% a 100%, pois a Gold não informa o percentual abaixo desse limite; valores ausentes ficam fora do filtro ([DEC-051](../docs/decisoes.md#dec-051--filtro-de-queda-na-fila-de-suspeitas)).
- Apenas o perfil `perdas` pode selecionar UCs e gerar OIs. A criação é atômica: uma UC inexistente ou com OI ativa impede todo o lote.
- Em telas estreitas ou para perfis sem permissão de edição, as ordens usam a tabela; a preferência de visualização é preservada.

## Design system

Os componentes reutilizáveis (backlog V2-02) são construídos e documentados no Storybook
antes de entrar nas telas. A configuração fica em `.storybook/`: ela reaproveita o
`vite.config.ts` (Tailwind, React Compiler, alias `#/`) sem os plugins do TanStack Start, e
carrega `src/styles.css`.

- **Fundamentos**: tokens da marca **VE-360** no `@theme` de `src/styles.css`
  (cores semânticas com tema escuro e claro via `data-tema="claro"`, primitivos para
  gráficos, tipografia, raio e sombra). As escalas padrão do Tailwind foram removidas;
  componentes não usam cor ou espaçamento solto.
- **Componentes** (`src/components/ui/`) e **Layout** (`src/components/layout/`): story em
  `<nome>.stories.tsx` ao lado do componente, cobrindo padrão, carregando, erro e vazio.
- **Checkbox** (`ui/checkbox/`): componente compartilhado pelo `DataTable` (tabela e cards) e pelos filtros de suspeitas, com os mesmos tamanho, borda, marca de seleção e animação. O painel de filtros usa opções de 32 px, padding reduzido e controles percentuais recolhíveis; os estados marcado, desmarcado, parcial e desabilitado estão no Storybook.
- Painel **Accessibility** (addon a11y) sem violações.
- Sem biblioteca de componentes como dependência. Componentes do
  [shadcn/ui](https://ui.shadcn.com/) (estilo `base-nova`, sobre Base UI) entram pela CLI (`npx shadcn@latest add <nome>`,
  configurada em `components.json`), são movidos para `ui/<nome>/<nome>.tsx` + `index.ts` e
  adaptados aos tokens. O [interior.dev](https://www.interior.dev/) é a referência de
  micro-interação.
- Ícones: [Phosphor](https://phosphoricons.com/) (`@phosphor-icons/react`), regras de
  tamanho, peso, cor e acessibilidade em **Fundamentos/Ícones**.
- Gráficos: SVG próprio com `motion`; `d3-scale` e `d3-shape` só para escalas e curvas
  (DEC-037). Cores das séries pelos tokens `chart-1` a `chart-6` e `chart-muted`. Tendência
  ao longo do tempo: `TrendChart` (área só com eixo a partir do zero, DEC-041); forma da série
  ao lado de um número: `Sparkline`; ponte de efeitos: `WaterfallChart`.

Regras e modelo de story na página **Introdução** do Storybook
(`.storybook/docs/introducao.mdx`).

## Convenções

- Dados da API: hooks com `useQuery`/`useMutation` chamando o `api.ts` da feature; após mutations, invalide as queries afetadas.
- Filtros de tela ficam na URL via `validateSearch` com Zod.
- Números e datas exibidos sempre via `src/lib/format.ts`.
- Testes: Vitest só para funções puras com regra de tela (conversões, limites), em `__tests__/` dentro da feature; sem DOM (DEC-026).
