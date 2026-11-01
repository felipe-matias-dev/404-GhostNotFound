import type { SortState } from "#/components/ui/data-table";
import { API_URL, api, unwrap } from "#/lib/api";
import type { Recorte } from "#/lib/filtros";
import {
	type AtualizarOrdem,
	type FiltrosFila,
	ORDENACAO_FILA,
	type OrdenacaoFila,
	type StatusOrdem,
} from "./types";

export const ordensKeys = {
	all: ["ordens-inspecao"] as const,
	lista: (status: StatusOrdem | undefined, recorte: Recorte) =>
		[...ordensKeys.all, { status, ...recorte }] as const,
	detalhe: (id: number) => [...ordensKeys.all, "detalhe", id] as const,
	// Começa por `all`: a invalidação por esse prefixo (aviso de mudança de ordem) renova o resumo.
	temposPorEtapa: ["ordens-inspecao", "tempos-por-etapa"] as const,
};

export const filaKey = ["fila-suspeitas"] as const;

/** Fluxo SSE do backend com os avisos de ordens criadas ou alteradas (`GET /ordens-inspecao/eventos`). */
export const URL_AVISOS_ORDENS = `${API_URL}/ordens-inspecao/eventos`;
export const distribuicaoQuedaKey = (recorte: Recorte) =>
	["distribuicao-queda", recorte] as const;
export const TAMANHO_PAGINA = 20;

const ordenacaoDaColuna = (coluna: string | undefined): OrdenacaoFila =>
	ORDENACAO_FILA.find((opcao) => opcao === coluna) ?? "prioridade";

export function distribuicaoQueda(recorte: Recorte) {
	return unwrap(
		api.GET("/fila-suspeitas/distribuicao-queda", {
			params: { query: recorte },
		}),
	);
}

export function listarFila(
	pagina: number,
	sort: SortState | null,
	filtros: FiltrosFila,
	recorte: Recorte,
) {
	return unwrap(
		api.GET("/fila-suspeitas", {
			params: {
				query: {
					...recorte,
					pagina,
					tamanho: TAMANHO_PAGINA,
					queda_min: filtros.queda?.[0],
					queda_max: filtros.queda?.[1],
					medidor_eletromecanico: filtros.medidorEletromecanico,
					leituras_estimadas_min: filtros.leiturasEstimadas?.[0],
					leituras_estimadas_max: filtros.leiturasEstimadas?.[1],
					ordenar_por: ordenacaoDaColuna(sort?.columnId),
					direcao: sort?.direction ?? "asc",
				},
			},
		}),
	);
}

export function listarOrdens(
	status: StatusOrdem | undefined,
	recorte: Recorte,
) {
	return unwrap(
		api.GET("/ordens-inspecao", {
			params: { query: { ...recorte, status } },
		}),
	);
}

export function temposPorEtapa() {
	return unwrap(api.GET("/ordens-inspecao/tempos-por-etapa"));
}

export function obterOrdem(id: number) {
	return unwrap(
		api.GET("/ordens-inspecao/{ordem_id}", {
			params: { path: { ordem_id: id } },
		}),
	);
}

export function atualizarOrdem(id: number, mudanca: AtualizarOrdem) {
	return unwrap(
		api.PATCH("/ordens-inspecao/{ordem_id}", {
			params: { path: { ordem_id: id } },
			body: mudanca,
		}),
	);
}

export function criarOrdens(codUcs: string[]) {
	return unwrap(api.POST("/ordens-inspecao", { body: { cod_ucs: codUcs } }));
}
