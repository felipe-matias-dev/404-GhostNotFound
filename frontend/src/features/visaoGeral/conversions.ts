import type { TrendCategory, TrendSeries } from "#/components/ui/trend-chart";
import type { WaterfallStep } from "#/components/ui/waterfall-chart";
import { trechoDe } from "#/features/filtros";
import type { Intervalo } from "#/features/indicadores";
import { formatCompetencia, formatCompetenciaCurta } from "#/lib/format";
import type { JanelaIndicadores } from "./types";

/** Janela máxima que `/indicadores/janelas` calcula; acima dela o gráfico fica indisponível. */
export const MESES_MAX_JANELA = 24;

/** Quantidade de meses de um período "AAAA-MM/AAAA-MM". */
export function mesesDoPeriodo(periodo: string): number {
	const { inicio, fim } = trechoDe(periodo);
	return fim - inicio + 1;
}

/** Só as janelas completas dentro do intervalo, como o backend as devolve. */
export function janelasDoIntervalo(
	janelas: JanelaIndicadores[],
	intervalo: Intervalo,
): JanelaIndicadores[] {
	return janelas.filter(
		(janela) =>
			janela.inicio >= intervalo.inicio && janela.fim <= intervalo.fim,
	);
}

export type Tesoura = {
	categories: TrendCategory[];
	series: TrendSeries[];
	/** As somas de `meses` meses por trás de cada ponto, para o tooltip. */
	somas: { receita: number; kwh: number }[];
};

/** Variação das somas calculadas pelo backend sobre a primeira janela exibida. */
export function tesoura(pontos: JanelaIndicadores[], meses: number): Tesoura {
	const base = pontos[0];
	if (!base || pontos.length < 2)
		return { categories: [], series: [], somas: [] };
	return {
		categories: pontos.map((p) => ({
			key: p.fim,
			label: formatCompetenciaCurta(p.fim),
			title: `${meses} ${meses === 1 ? "mês" : "meses"} até ${formatCompetencia(p.fim)}`,
		})),
		series: [
			{
				id: "receita",
				label: "Receita faturada",
				shortLabel: "receita",
				values: pontos.map((p) =>
					base.receita_faturada === 0
						? null
						: p.receita_faturada / base.receita_faturada - 1,
				),
				color: 1,
				emphasis: true,
			},
			{
				id: "kwh",
				label: "Energia faturada",
				shortLabel: "energia",
				values: pontos.map((p) =>
					base.kwh_faturado === 0
						? null
						: p.kwh_faturado / base.kwh_faturado - 1,
				),
				color: 2,
				emphasis: true,
			},
		],
		somas: pontos.map((p) => ({
			receita: p.receita_faturada,
			kwh: p.kwh_faturado,
		})),
	};
}

// Direção da variação já arredondada a uma casa, como a seta do KpiDelta: 0,04% é estável.
const direcao = (pct: number) => Math.sign(Math.round(pct * 10));

/**
 * A frase do topo da tela, só pela direção e pelo tamanho relativo das duas variações (em %,
 * como vêm da API). Os números ficam nos indicadores logo abaixo, e não se repetem aqui.
 */
export function leitura(
	receitaPct: number | null | undefined,
	kwhPct: number | null | undefined,
): string | null {
	if (receitaPct == null || kwhPct == null) return null;
	const r = direcao(receitaPct);
	const k = direcao(kwhPct);
	const ritmo = direcao(receitaPct - kwhPct);
	if (r > 0) {
		if (k < 0) return "A receita cresceu com menos energia faturada.";
		if (k === 0) return "A receita cresceu com a mesma energia faturada.";
		if (ritmo > 0) return "A receita cresceu mais que a energia faturada.";
		if (ritmo < 0) return "A receita cresceu menos que a energia faturada.";
		return "Receita e energia faturada cresceram no mesmo ritmo.";
	}
	if (r === 0) {
		if (k > 0) return "A receita ficou estável com mais energia faturada.";
		if (k < 0) return "A receita ficou estável com menos energia faturada.";
		return "Receita e energia faturada ficaram estáveis.";
	}
	if (k > 0) return "A receita caiu mesmo com mais energia faturada.";
	if (k === 0) return "A receita caiu com a mesma energia faturada.";
	if (ritmo < 0) return "A receita caiu mais que a energia faturada.";
	if (ritmo > 0) return "A receita caiu menos que a energia faturada.";
	return "Receita e energia faturada caíram no mesmo ritmo.";
}

export type EfeitoDaReceita = {
	id: string;
	rotulo: string;
	pct: number | null;
};

/**
 * Os efeitos da ponte de receita como peso sobre a receita base, como a tela de Receita mostra
 * em % (DEC-035). Em % e não em R$: a ponte é sobre a receita de energia e o resumo, sobre a
 * faturada; o peso de cada efeito é o mesmo nas duas medidas, o valor em reais não.
 */
export function efeitosDaReceita(passos: WaterfallStep[]): EfeitoDaReceita[] {
	const base = passos.find((p) => p.kind === "total")?.value ?? 0;
	return passos
		.filter((p) => p.kind === "delta")
		.map((p) => ({
			id: p.id,
			rotulo: p.label,
			pct: base > 0 ? p.value / base : null,
		}));
}
