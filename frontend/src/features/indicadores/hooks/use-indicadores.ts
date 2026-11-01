import { skipToken, useQuery } from "@tanstack/react-query";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import {
	buscarComparacaoIndicadores,
	buscarIndicadoresMensais,
	indicadoresKeys,
} from "../api";

/** A série mensal do recorte no intervalo dos dois períodos: sparklines e referências. */
export function useIndicadoresMensais(
	par: ParPeriodos | undefined,
	recorte: Recorte,
) {
	return useQuery({
		queryKey: indicadoresKeys.mensal(par, recorte),
		queryFn: par ? () => buscarIndicadoresMensais(par, recorte) : skipToken,
	});
}

/** Os indicadores do recorte nos dois períodos e a variação, todos calculados no backend. */
export function useComparacaoIndicadores(
	par: ParPeriodos | undefined,
	recorte: Recorte,
) {
	return useQuery({
		queryKey: indicadoresKeys.comparacao(par, recorte),
		queryFn: par ? () => buscarComparacaoIndicadores(par, recorte) : skipToken,
	});
}
