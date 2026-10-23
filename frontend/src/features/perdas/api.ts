import { api, unwrap } from "#/lib/api";
import type { AtualizarOrdem, StatusOrdem } from "./types";

export const ordensKeys = {
	all: ["ordens-inspecao"] as const,
	lista: (status: StatusOrdem | undefined) =>
		[...ordensKeys.all, { status }] as const,
	detalhe: (id: number) => [...ordensKeys.all, "detalhe", id] as const,
};

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
