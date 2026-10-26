import type { components, operations } from "#/lib/api-schema.gen";

export type DecomposicaoLinha =
	components["schemas"]["DecomposicaoLinhaSchema"];

export type DecomposicaoFiltro = NonNullable<
	operations["get_decomposicao_receita_decomposicao_get"]["parameters"]["query"]
>;

export type ParPeriodos = components["schemas"]["ParPeriodosSchema"];

/** Onde o usuário está no drill-down (vem da URL). */
export type Recorte = { municipio?: string; bairro?: string };
