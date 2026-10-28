import { Link } from "@tanstack/react-router";
import type { ReactElement } from "react";
import { KpiCard } from "#/components/ui/kpi-card";
import { Sparkline } from "#/components/ui/sparkline";
import { cn } from "#/lib/utils";
import { mesDoPeriodo } from "../conversions";
import {
	useComparacaoIndicadores,
	useKpisMensais,
} from "../hooks/use-indicadores";
import { DEFINICOES } from "../indicadores";
import type { Indicador, ParPeriodos } from "../types";
import { ComparacaoPicker } from "./comparacao-picker";

// Receita e energia ficam no resumo de 12 meses: repetidas aqui, num mês, com o mesmo nome,
// seriam duas "receitas" com variações diferentes.
const DA_FAIXA = [
	"dec",
	"fec",
	"n_chamados",
	"satisfacao_media",
] as const satisfies readonly Indicador[];

const LINKS: Partial<Record<Indicador, ReactElement>> = {
	dec: <Link to="/rede" />,
	fec: <Link to="/rede" />,
};

/**
 * Rede e atendimento no mês escolhido, numa faixa só, cada um com a variação sobre o mês base
 * e a forma da série inteira (o mês atual em destaque, o base em anel). O mês contra mês é o
 * que a tela usa para DEC, FEC e satisfação até passar para a rota de comparação (DEC-041).
 */
export function IndicadoresMes({
	competencias,
	par,
	onEscolher,
	carregando,
	erro,
	semDados,
	onRetry,
}: {
	competencias: string[];
	par: ParPeriodos | undefined;
	onEscolher: (par: ParPeriodos) => void;
	carregando: boolean;
	erro: string | null;
	/** A Gold não tem dois meses para comparar: todos os indicadores ficam vazios. */
	semDados: boolean;
	onRetry: () => void;
}) {
	const comparacao = useComparacaoIndicadores(par);
	const serie = useKpisMensais();
	const linhas = serie.data ?? [];
	const indiceDe = (periodo: string | undefined) => {
		const mes = mesDoPeriodo(periodo);
		const i = linhas.findIndex((linha) => linha.competencia === mes);
		return i < 0 ? undefined : i;
	};
	const atual = indiceDe(par?.periodo_atual);
	const base = indiceDe(par?.periodo_base);

	return (
		<section
			aria-labelledby="mes-titulo"
			className="@container flex min-w-0 flex-col overflow-hidden rounded-md border border-border bg-surface-1 shadow-edge"
		>
			<div className="flex flex-wrap items-center justify-between gap-2 px-5 pt-4 pb-3">
				<h2 id="mes-titulo" className="text-heading">
					Rede e atendimento no mês
				</h2>
				<ComparacaoPicker
					competencias={competencias}
					par={par}
					onEscolher={onEscolher}
					semPeriodos={Boolean(erro) || semDados}
				/>
			</div>
			<div className="grid grid-cols-2 gap-px border-border border-t bg-border @2xl:grid-cols-4">
				{DA_FAIXA.map((indicador) => {
					const definicao = DEFINICOES[indicador];
					const variacao = comparacao.data?.variacao[indicador];
					const valores = linhas.map((linha) => linha[indicador] ?? null);
					return (
						<KpiCard
							key={indicador}
							label={definicao.label}
							value={
								semDados ? null : comparacao.data?.atual.valores[indicador]
							}
							format={definicao.format}
							hint={definicao.hint}
							link={LINKS[indicador]}
							loading={carregando}
							error={erro}
							onRetry={onRetry}
							emptyMessage={
								semDados ? "Sem indicadores carregados." : "Sem dado no mês."
							}
							delta={
								variacao == null
									? undefined
									: { value: variacao, favorable: definicao.favorable }
							}
							// Card inteiro é o link: o fundo responde ao hover, e o chevron diz para onde.
							className={cn(
								"rounded-none border-0 px-5 py-4 shadow-none",
								LINKS[indicador] && "hover:bg-surface-2",
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
