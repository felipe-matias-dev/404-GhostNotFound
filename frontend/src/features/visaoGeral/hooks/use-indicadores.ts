import { skipToken, useQuery } from "@tanstack/react-query";
import { intervaloDoPar } from "#/features/indicadores";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { buscarJanelas, visaoGeralKeys } from "../api";
import {
	janelasDoIntervalo,
	MESES_MAX_JANELA,
	mesesDoPeriodo,
	tesoura,
} from "../conversions";

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
			tesoura(intervalo ? janelasDoIntervalo(linhas, intervalo) : [], meses),
	});
}
