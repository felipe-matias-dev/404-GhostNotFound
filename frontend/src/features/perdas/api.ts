import { api, unwrap } from "#/lib/api";
import type { StatusOrdem } from "./types";

export const ordensKeys = {
	all: ["ordens-inspecao"] as const,
	lista: (status: StatusOrdem | undefined) =>
		[...ordensKeys.all, { status }] as const,
};

export function listarOrdens(status: StatusOrdem | undefined) {
	return unwrap(api.GET("/ordens-inspecao", { params: { query: { status } } }));
}
