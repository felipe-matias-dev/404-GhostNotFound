import { skipToken, useQuery } from "@tanstack/react-query";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import {
	buscarComparacaoIndicadores,
	buscarIndicadoresMensais,
	buscarJanelas,
	visaoGeralKeys,
} from "../api";
import {
	intervaloDoPar,
	janelasDoIntervalo,
	MESES_MAX_JANELA,
	mesesDoPeriodo,
	tesoura,
} from "../conversions";

/** A série mensal do recorte no intervalo dos dois períodos: a forma de cada sparkline. */
export function useIndicadoresMensais(
	par: ParPeriodos | undefined,
	recorte: Recorte,
) {
	return useQuery({
		queryKey: visaoGeralKeys.mensal(par, recorte),
		queryFn: par ? () => buscarIndicadoresMensais(par, recorte) : skipToken,
	});
}

export function useComparacaoIndicadores(
	par: ParPeriodos | undefined,
	recorte: Recorte,
) {
	return useQuery({
		queryKey: visaoGeralKeys.comparacao(par, recorte),
		queryFn: par ? () => buscarComparacaoIndicadores(par, recorte) : skipToken,
	});
}

/**
 * A tesoura do par: janelas do tamanho do período atual, recortadas ao intervalo dos dois
 * períodos. Acima do limite do gráfico, a consulta nem sai.
 */
export function useTesoura(par: ParPeriodos | undefined, recorte: Recorte) {
	const meses = par ? mesesDoPeriodo(par.periodo_atual) : 0;
	const intervalo = par ? intervaloDoPar(par) : undefined;
	return useQuery({
		queryKey: visaoGeralKeys.janelas(meses, recorte),
		queryFn:
			meses > 0 && meses <= MESES_MAX_JANELA
				? () => buscarJanelas(meses, recorte)
				: skipToken,
		select: (linhas) =>
			tesoura(
				intervalo ? janelasDoIntervalo(linhas, intervalo) : [],
				meses,
			),
	});
}
