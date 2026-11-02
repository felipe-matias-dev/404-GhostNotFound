import type { ParPeriodos } from "#/lib/filtros";

export type Intervalo = { inicio: string; fim: string };

/** Do menor início ao maior fim dos dois períodos do par, inclusive. */
export function intervaloDoPar(par: ParPeriodos): Intervalo {
	const [baseInicio = "", baseFim = ""] = par.periodo_base.split("/");
	const [atualInicio = "", atualFim = ""] = par.periodo_atual.split("/");
	return {
		inicio: baseInicio < atualInicio ? baseInicio : atualInicio,
		fim: baseFim > atualFim ? baseFim : atualFim,
	};
}
