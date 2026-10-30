import type { components } from "#/lib/api-schema.gen";

export type Ordem = components["schemas"]["OrdemSchema"];
export type OrdemDetalhe = components["schemas"]["OrdemDetalheSchema"];
export type EventoOrdem = components["schemas"]["EventoSchema"];
export type AtualizarOrdem = components["schemas"]["AtualizarOrdemSchema"];
export type StatusOrdem = components["schemas"]["StatusOrdem"];
export type ResultadoOrdem = components["schemas"]["ResultadoOrdem"];

/** Na ordem da máquina de estados; valida o `?status=` da URL. */
export const STATUS_ORDEM = [
	"GERADA",
	"EM_CAMPO",
	"CONCLUIDA",
	"CANCELADA",
] as const satisfies readonly StatusOrdem[];

export const RESULTADO_ORDEM = [
	"IRREGULAR_CONFIRMADA",
	"REGULAR",
	"NAO_REALIZADA",
] as const satisfies readonly ResultadoOrdem[];

/** Mudanças de status que a tela oferece; cada uma leva a um status (`STATUS_DESTINO`). */
export type AcaoOrdem = "enviar" | "concluir" | "cancelar";

/** Limite de UCs por pedido, espelhando `MAX_ORDENS_POR_PEDIDO` de `backend/src/venergy_api/schemas.py`. */
export const MAX_ORDENS_POR_PEDIDO = 200;

export type VisaoOrdens = "kanban" | "tabela";

export type FiltrosFila = {
	queda: [number, number] | null;
	medidorEletromecanico: boolean;
	leiturasEstimadas: [number, number] | null;
};

export const FILTROS_FILA_INICIAIS: FiltrosFila = {
	queda: null,
	medidorEletromecanico: false,
	leiturasEstimadas: null,
};
