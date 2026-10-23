import type { ResultadoOrdem, StatusOrdem } from "./types";

/** Rótulo e cor do ponto do badge (Fundamentos/Estados) de cada status da OI. */
export const STATUS_ORDEM_VISUAL: Record<
	StatusOrdem,
	{ rotulo: string; ponto: string }
> = {
	GERADA: { rotulo: "Gerada", ponto: "bg-accent" },
	EM_CAMPO: { rotulo: "Em campo", ponto: "bg-info" },
	CONCLUIDA: { rotulo: "Concluída", ponto: "bg-success" },
	CANCELADA: { rotulo: "Cancelada", ponto: "bg-text-muted" },
};

export const RESULTADO_ORDEM_ROTULO: Record<ResultadoOrdem, string> = {
	IRREGULAR_CONFIRMADA: "Irregularidade confirmada",
	REGULAR: "Regular",
	NAO_REALIZADA: "Não realizada",
};
