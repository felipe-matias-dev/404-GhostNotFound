import { Link } from "@tanstack/react-router";
import type { ReactElement } from "react";
import { KpiCard } from "#/components/ui/kpi-card";
import { Sparkline } from "#/components/ui/sparkline";
import { INDICADORES, mesDoPeriodo } from "../conversions";
import {
	useComparacaoIndicadores,
	useKpisMensais,
} from "../hooks/use-indicadores";
import { DEFINICOES } from "../indicadores";
import type { Indicador, ParPeriodos } from "../types";
import { ComparacaoPicker } from "./comparacao-picker";

const LINKS: Partial<
	Record<Indicador, (par: ParPeriodos | undefined) => ReactElement>
> = {
	receita_faturada: (par) => (
		<Link
			to="/receita"
			search={{
				periodo_base: par?.periodo_base,
				periodo_atual: par?.periodo_atual,
			}}
		/>
	),
	dec: () => <Link to="/rede" />,
	fec: () => <Link to="/rede" />,
};

/**
 * Os seis indicadores do mês escolhido numa faixa só, cada um com a variação sobre o mês base
 * e a forma da série inteira (o mês atual em destaque, o base em anel). O mês contra mês é o
 * que a API permite para DEC, FEC e satisfação até existir a rota de comparação (DEC-036).
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
		<section aria-labelledby="mes-titulo" className="flex flex-col gap-3">
			<div className="flex flex-wrap items-center justify-between gap-2">
				<h2 id="mes-titulo" className="text-heading">
					Indicadores do mês
				</h2>
				<ComparacaoPicker
					competencias={competencias}
					par={par}
					onEscolher={onEscolher}
					semPeriodos={Boolean(erro) || semDados}
				/>
			</div>
			<div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-border bg-border lg:grid-cols-3 xl:grid-cols-6">
				{INDICADORES.map((indicador) => {
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
							link={LINKS[indicador]?.(par)}
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
							className="rounded-none border-0 p-4 shadow-none"
						>
							<Sparkline values={valores} highlight={atual} reference={base} />
						</KpiCard>
					);
				})}
			</div>
		</section>
	);
}
