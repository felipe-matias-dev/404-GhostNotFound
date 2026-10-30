import { api, unwrap } from "#/lib/api";
import type { Uc360 } from "./types";

export const unidadeConsumidoraKeys = {
	visao360: (codUc: string | undefined) =>
		["unidadeConsumidora", "visao360", codUc] as const,
};

export function buscarVisao360(
	codUc: string,
	signal?: AbortSignal,
): Promise<Uc360> {
	return unwrap(
		api.GET("/unidades-consumidoras/{cod_uc}/visao-360", {
			params: { path: { cod_uc: codUc } },
			signal,
		}),
	);
}
