import type { components, operations } from "#/lib/api-schema.gen";

export type DecomposicaoLinha =
	components["schemas"]["DecomposicaoLinhaSchema"];

export type DecomposicaoFiltro = NonNullable<
	operations["get_decomposicao_receita_decomposicao_get"]["parameters"]["query"]
>;

export type ParPeriodos = components["schemas"]["ParPeriodosSchema"];

export type Classe = NonNullable<DecomposicaoFiltro["classe"]>;

/**
 * Onde o usuário está (vem da URL): o drill-down município → bairro e, à parte, a classe, que
 * filtra todos os níveis.
 */
export type Recorte = { municipio?: string; bairro?: string; classe?: Classe };
