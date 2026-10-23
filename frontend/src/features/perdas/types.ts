import type { components } from "#/lib/api-schema.gen";

export type Ordem = components["schemas"]["OrdemSchema"];
export type StatusOrdem = components["schemas"]["StatusOrdem"];
export type ResultadoOrdem = components["schemas"]["ResultadoOrdem"];

/** Na ordem da máquina de estados; valida o `?status=` da URL. */
export const STATUS_ORDEM = [
	"GERADA",
	"EM_CAMPO",
	"CONCLUIDA",
	"CANCELADA",
] as const satisfies readonly StatusOrdem[];
