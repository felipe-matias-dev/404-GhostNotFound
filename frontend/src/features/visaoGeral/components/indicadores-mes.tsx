import { Link } from "@tanstack/react-router";
import type { ReactElement } from "react";
import { KpiCard } from "#/components/ui/kpi-card";
import { Sparkline } from "#/components/ui/sparkline";
import { useFiltrosPortal } from "#/features/filtros";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { cn } from "#/lib/utils";
import {
	useComparacaoIndicadores,
	useIndicadoresMensais,
} from "../hooks/use-indicadores";
import { DEFINICOES } from "../indicadores";
import type { Indicador } from "../types";

// Receita e energia ficam no resumo: repetidas aqui, no mesmo período, com o mesmo nome,
// seriam duas "receitas" com variações diferentes.
const DA_FAIXA = [
	"dec",
	"fec",
	"n_chamados",
	"satisfacao_media",
] as const satisfies readonly Indicador[];

/**
 * Rede e atendimento no período escolhido, numa faixa só, cada um com a variação sobre a base
 * e a forma da série no recorte (o último mês de cada período em destaque). Valores e variações
 * vêm da comparação do backend; a série mensal serve só às sparklines.
 */
export function IndicadoresMes({
	par,
	recorte,
	carregando,
	semPeriodo,
}: {
	par: ParPeriodos | undefined;
	recorte: Recorte;
	/** O período padrão ainda não foi resolvido pela barra comum. */
	carregando: boolean;
	/** A Gold não tem dois meses para comparar: todos os indicadores ficam vazios. */
	semPeriodo: boolean;
}) {
	const { searchPara } = useFiltrosPortal();
	const comparacao = useComparacaoIndicadores(par, recorte);
	const serie = useIndicadoresMensais(par, recorte);
	const linhas = serie.data ?? [];
	const indiceDe = (competencia: string | undefined) => {
		const indice = linhas.findIndex(
			(linha) => linha.competencia === competencia,
		);
		return indice < 0 ? undefined : indice;
	};
	const atual = indiceDe(par?.periodo_atual.split("/")[1]);
	const base = indiceDe(par?.periodo_base.split("/")[1]);

	const links: Partial<Record<Indicador, ReactElement>> = {
		dec: (
			<Link
				to="/rede"
				search={searchPara("/rede", { criterio: "dec" }) as never}
			/>
		),
		fec: (
			<Link
				to="/rede"
				search={searchPara("/rede", { criterio: "fec" }) as never}
			/>
		),
	};

	return (
		<section
			aria-labelledby="mes-titulo"
			className="@container flex min-w-0 flex-col overflow-hidden rounded-md border border-border bg-surface-1 shadow-edge"
		>
			<div className="flex flex-wrap items-center justify-between gap-2 px-5 pt-4 pb-3">
				<h2 id="mes-titulo" className="text-heading">
					Rede e atendimento no período
				</h2>
			</div>
			<div className="grid grid-cols-2 gap-px border-border border-t bg-border @2xl:grid-cols-4">
				{DA_FAIXA.map((indicador) => {
					const definicao = DEFINICOES[indicador];
					const variacao = comparacao.data?.variacao_pct[indicador];
					const valores = linhas.map((linha) => linha[indicador] ?? null);
					return (
						<KpiCard
							key={indicador}
							label={definicao.label}
							value={
								semPeriodo || comparacao.data?.atual.n_meses === 0
									? null
									: comparacao.data?.atual[indicador]
							}
							format={definicao.format}
							hint={definicao.hint}
							link={links[indicador]}
							loading={carregando || (Boolean(par) && comparacao.isPending)}
							error={
								comparacao.isError
									? "Não foi possível carregar os indicadores."
									: null
							}
							onRetry={() => void comparacao.refetch()}
							emptyMessage={
								semPeriodo ? "Sem período selecionado." : "Sem dado no período."
							}
							delta={
								variacao == null
									? undefined
									: { value: variacao / 100, favorable: definicao.favorable }
							}
							// Card inteiro é o link: o fundo responde ao hover, e o chevron diz para onde.
							className={cn(
								"rounded-none border-0 px-5 py-4 shadow-none",
								links[indicador] && "hover:bg-surface-2",
							)}
						>
							<Sparkline values={valores} highlight={atual} reference={base} />
						</KpiCard>
					);
				})}
			</div>
		</section>
	);
}
