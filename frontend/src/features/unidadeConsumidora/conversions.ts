import type { TrendCategory, TrendSeries } from "#/components/ui/trend-chart";
import { formatCompetencia, formatCompetenciaCurta } from "#/lib/format";
import type { ConsumoMesUc, VariacaoConta } from "./types";

export function toConsumoChart(consumo: ConsumoMesUc[]): {
	categories: TrendCategory[];
	series: TrendSeries[];
} {
	return {
		categories: consumo.map((row) => {
			const [ano, mes] = row.competencia.split("-");
			const anterior = `${Number(ano) - 1}-${mes}`;
			return {
				key: row.competencia,
				label: formatCompetenciaCurta(row.competencia),
				title: `${formatCompetencia(row.competencia)} / ${formatCompetencia(anterior)}`,
			};
		}),
		series: [
			{
				id: "atual",
				label: "Últimos 12 meses",
				color: 1,
				emphasis: true,
				values: consumo.map((row) => row.kwh_faturado),
			},
			{
				id: "ano-anterior",
				label: "Mesmo período do ano anterior",
				color: 2,
				values: consumo.map((row) => row.kwh_ano_anterior),
			},
		],
	};
}

export type ParteDaConta = {
	id: "consumo" | "tarifa" | "bandeira" | "tributos";
	rotulo: string;
	/** Quanto esta parte somou (positivo) ou tirou (negativo) da conta, em R$. */
	valor: number;
};

/**
 * Partes da variação da conta na ordem fixa do card (DEC-057). Os dias faturados não são uma
 * parte: o consumo leva todo o volume. Os valores vêm prontos do backend e somam a `diferenca`:
 * a tela não recalcula nada.
 */
export function partesDaConta(variacao: VariacaoConta): ParteDaConta[] {
	return [
		{ id: "consumo", rotulo: "Consumo", valor: variacao.consumo },
		{ id: "tarifa", rotulo: "Tarifa", valor: variacao.tarifa },
		{ id: "bandeira", rotulo: "Bandeira", valor: variacao.bandeira },
		{ id: "tributos", rotulo: "Tributos", valor: variacao.tributos },
	];
}

function diasPorExtenso(dias: number): string {
	return `${dias} ${dias === 1 ? "dia" : "dias"}`;
}

/**
 * Quantos dias cada conta cobriu, só como informação: o kWh não acompanha os dias faturados, por
 * isso eles não entram na divisão (DEC-057). A atendente vê quando uma conta cobriu bem mais dias
 * que a outra. Vazio quando nenhuma das contas traz os dias.
 */
export function textoDosDias(variacao: VariacaoConta): string | null {
	const { dias_faturados: atual, dias_faturados_comparada: comparada } =
		variacao;
	if (atual !== null && comparada !== null) {
		return `Esta conta cobriu ${diasPorExtenso(atual)}; a do ano anterior, ${comparada}.`;
	}
	if (atual !== null) return `Esta conta cobriu ${diasPorExtenso(atual)}.`;
	if (comparada !== null) {
		return `A conta do ano anterior cobriu ${diasPorExtenso(comparada)}.`;
	}
	return null;
}

/**
 * A parte que mais pesou na direção da conta: com a conta subindo, a maior que encareceu; com a
 * conta caindo, a maior que barateou. Uma parte no sentido contrário não explica a variação. No
 * empate, a primeira da ordem do card; com a conta igual, nenhuma.
 */
export function maiorParte(
	partes: ParteDaConta[],
	diferenca: number,
): ParteDaConta | null {
	// Conta igual: nada pesou, mesmo que as partes tenham se compensado.
	if (diferenca === 0) return null;
	let maior: ParteDaConta | null = null;
	for (const parte of partes) {
		if (Math.sign(parte.valor) !== Math.sign(diferenca) || parte.valor === 0)
			continue;
		if (maior === null || Math.abs(parte.valor) > Math.abs(maior.valor)) {
			maior = parte;
		}
	}
	return maior;
}
