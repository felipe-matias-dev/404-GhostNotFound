import { Link } from "@tanstack/react-router";
import type { ReactElement } from "react";
import { KpiCard } from "#/components/ui/kpi-card";
import { formatPeriodoCurto } from "#/lib/format";
import { DEFINICOES, GRUPOS } from "../indicadores";
import type { ComparacaoIndicadores, Indicador, ParPeriodos } from "../types";

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
 * Os seis indicadores da diretoria em três grupos, cada um com o valor do período atual e a
 * variação sobre a base (verde quando melhora, vermelho quando piora).
 */
export function IndicadoresCards({
	comparacao,
	par,
	carregando,
	erro,
	semDados,
	onRetry,
}: {
	comparacao: ComparacaoIndicadores | undefined;
	par: ParPeriodos | undefined;
	carregando: boolean;
	erro: string | null;
	/** A Gold não tem nenhum mês para comparar: todos os cards ficam vazios. */
	semDados: boolean;
	onRetry: () => void;
}) {
	const comparacaoTexto = par
		? `vs. ${formatPeriodoCurto(par.periodo_base)}`
		: undefined;
	return (
		<div className="grid gap-5 xl:grid-cols-3">
			{GRUPOS.map((grupo) => (
				<section
					key={grupo.id}
					aria-labelledby={`grupo-${grupo.id}`}
					className="flex min-w-0 flex-col gap-3"
				>
					<h2 id={`grupo-${grupo.id}`} className="text-heading">
						{grupo.titulo}
					</h2>
					<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
						{grupo.indicadores.map((indicador) => {
							const definicao = DEFINICOES[indicador];
							const valor = semDados
								? null
								: comparacao?.atual.valores[indicador];
							const variacao = comparacao?.variacao[indicador];
							return (
								<KpiCard
									key={indicador}
									label={definicao.label}
									value={valor}
									format={definicao.format}
									hint={definicao.hint}
									link={LINKS[indicador]?.(par)}
									highlight={indicador === "receita_faturada"}
									loading={carregando}
									error={erro}
									onRetry={onRetry}
									emptyMessage={
										semDados
											? "Sem indicadores carregados."
											: "Sem dados no período."
									}
									delta={
										variacao == null
											? undefined
											: {
													value: variacao,
													favorable: definicao.favorable,
													comparison: comparacaoTexto,
												}
									}
								/>
							);
						})}
					</div>
				</section>
			))}
		</div>
	);
}
