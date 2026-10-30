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
	id: "consumo" | "dias" | "tarifa" | "bandeira" | "tributos";
	rotulo: string;
	/** Quanto esta parte somou (positivo) ou tirou (negativo) da conta, em R$. */
	valor: number;
};

/**
 * Partes da variação da conta na ordem fixa do card (DEC-052). "Dias" só entra quando a API a
 * separa do consumo; vazia, todo o volume já está em "consumo". Os valores vêm prontos do
 * backend e somam a `diferenca`: a tela não recalcula nada.
 */
export function partesDaConta(variacao: VariacaoConta): ParteDaConta[] {
	const partes: ParteDaConta[] = [
		{ id: "consumo", rotulo: "Consumo", valor: variacao.consumo },
	];
	if (variacao.dias !== null) {
		partes.push({ id: "dias", rotulo: "Dias na fatura", valor: variacao.dias });
	}
	partes.push(
		{ id: "tarifa", rotulo: "Tarifa", valor: variacao.tarifa },
		{ id: "bandeira", rotulo: "Bandeira", valor: variacao.bandeira },
		{ id: "tributos", rotulo: "Tributos", valor: variacao.tributos },
	);
	return partes;
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
