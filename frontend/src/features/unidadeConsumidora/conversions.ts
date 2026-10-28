import type { TrendCategory, TrendSeries } from "#/components/ui/trend-chart";
import { formatCompetencia, formatCompetenciaCurta } from "#/lib/format";
import type { ConsumoMesUc } from "./types";

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
