import type { SortState } from "#/components/ui/data-table";
import { api, unwrap } from "#/lib/api";
import type { AtualizarOrdem, FiltrosFila, StatusOrdem } from "./types";

export const ordensKeys = {
	all: ["ordens-inspecao"] as const,
	lista: (status: StatusOrdem | undefined) =>
		[...ordensKeys.all, { status }] as const,
	detalhe: (id: number) => [...ordensKeys.all, "detalhe", id] as const,
};

export const filaKey = ["fila-suspeitas"] as const;
export const TAMANHO_PAGINA = 20;

export function distribuicaoQueda() {
	return unwrap(api.GET("/fila-suspeitas/distribuicao-queda"));
}

export function listarFila(
	pagina: number,
	sort: SortState | null,
	filtros: FiltrosFila,
) {
	return unwrap(
		api.GET("/fila-suspeitas", {
			params: {
				query: {
					pagina,
					tamanho: TAMANHO_PAGINA,
					queda_min: filtros.queda?.[0],
					queda_max: filtros.queda?.[1],
					medidor_eletromecanico: filtros.medidorEletromecanico,
					leituras_estimadas_min: filtros.leiturasEstimadas?.[0],
					leituras_estimadas_max: filtros.leiturasEstimadas?.[1],
					ordenar_por:
						sort?.columnId === "queda"
							? "queda"
							: sort?.columnId === "energia"
								? "energia"
								: sort?.columnId === "ordem_ativa"
									? "ordem_ativa"
									: "prioridade",
					direcao: sort?.direction ?? "asc",
				},
			},
		}),
	);
}

export function listarOrdens(status: StatusOrdem | undefined) {
	return unwrap(api.GET("/ordens-inspecao", { params: { query: { status } } }));
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
