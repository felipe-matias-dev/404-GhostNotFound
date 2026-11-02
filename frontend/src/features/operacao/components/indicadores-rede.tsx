import type { ReactElement } from "react";
import { KpiCard } from "#/components/ui/kpi-card";
import { Sparkline } from "#/components/ui/sparkline";
import {
	useComparacaoIndicadores,
	useIndicadoresMensais,
} from "#/features/indicadores";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { formatPeriodoCurto } from "#/lib/format";
import { INDICADORES_REDE, type IndicadorRede } from "../indicadores";

const DA_FAIXA = [
	"dec",
	"fec",
	"horas_interrompidas",
	"n_interrupcoes",
	"n_uc_medio",
] as const satisfies readonly IndicadorRede[];

/**
 * Continuidade do recorte inteiro no período atual, cada indicador com a variação sobre a base.
 * Valores e variações vêm da comparação do backend, com a mesma conta da tabela; a série mensal
 * serve só aos minigráficos (o último mês de cada período em destaque).
 */
export function IndicadoresRede({
	titulo,
	periodoAtual,
	periodoBase,
	recorte,
}: {
	titulo: string;
	periodoAtual: string;
	/** Sem base (início da base de dados), não há com o que comparar. */
	periodoBase: string | undefined;
	recorte: Recorte;
}): ReactElement {
	const par: ParPeriodos | undefined = periodoBase
		? { periodo_base: periodoBase, periodo_atual: periodoAtual }
		: undefined;
	const comparacao = useComparacaoIndicadores(par, recorte);
	const serie = useIndicadoresMensais(par, recorte);
	const linhas = serie.data ?? [];
	const indiceDe = (competencia: string | undefined) => {
		const indice = linhas.findIndex(
			(linha) => linha.competencia === competencia,
		);
		return indice < 0 ? undefined : indice;
	};
	const atual = indiceDe(periodoAtual.split("/")[1]);
	const base = indiceDe(periodoBase?.split("/")[1]);
	const semDado = comparacao.data?.atual.n_meses === 0;

	return (
		<section
			aria-labelledby="rede-indicadores-titulo"
			className="@container flex min-w-0 flex-col overflow-hidden rounded-md border border-border bg-surface-1 shadow-edge"
		>
			<div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 px-5 pt-4 pb-3">
				<h2 id="rede-indicadores-titulo" className="text-heading">
					{titulo}
				</h2>
				<p className="text-small text-text-muted">
					{formatPeriodoCurto(periodoAtual)}
					{periodoBase
						? `, comparado com ${formatPeriodoCurto(periodoBase)}`
						: ", sem período base para comparar"}
				</p>
			</div>
			<div className="grid grid-cols-2 gap-px border-border border-t bg-border @4xl:grid-cols-5">
				{DA_FAIXA.map((indicador) => {
					const definicao = INDICADORES_REDE[indicador];
					const variacao = comparacao.data?.variacao_pct[indicador];
					return (
						<KpiCard
							key={indicador}
							label={definicao.label}
							value={!par || semDado ? null : comparacao.data?.atual[indicador]}
							format={definicao.format}
							hint={definicao.hint}
							loading={Boolean(par) && comparacao.isPending}
							error={
								comparacao.isError
									? "Não foi possível carregar os indicadores."
									: null
							}
							onRetry={() => void comparacao.refetch()}
							emptyMessage={par ? "Sem dado no período." : "Sem período base."}
							delta={
								variacao == null || !periodoBase
									? undefined
									: {
											value: variacao / 100,
											favorable: definicao.favorable,
											comparison: `vs. ${formatPeriodoCurto(periodoBase)}`,
										}
							}
							// Em duas colunas, o quinto card ocupa a linha inteira em vez de deixar um buraco.
							className="rounded-none border-0 px-5 py-4 shadow-none last:col-span-2 @4xl:last:col-span-1"
						>
							{/* A série mensal do recorte só tem os índices: os totais ficam sem minigráfico. */}
							{(indicador === "dec" || indicador === "fec") && (
								<Sparkline
									values={linhas.map((linha) => linha[indicador] ?? null)}
									highlight={atual}
									reference={base}
								/>
							)}
						</KpiCard>
					);
				})}
			</div>
		</section>
	);
}
