import { Link } from "@tanstack/react-router";
import type { ReactElement } from "react";
import { KpiCard } from "#/components/ui/kpi-card";
import { formatPeriodoCurto } from "#/lib/format";
import { DEFINICOES, GRUPOS } from "../indicadores";
import type { ComparacaoIndicadores, Indicador, ParPeriodos } from "../types";

const LINKS: Partial<Record<Indicador, ReactElement>> = {
	// TODO: quando a ponte de receita aceitar o par de meses desta tela (DEC-036), passar
	// `periodo_base` e `periodo_atual` no link. Hoje a `ReceitaPage` descarta pares que não
	// estão em `gold_receita_decomposicao` e abre no período padrão dela.
	receita_faturada: (
		<Link
			to="/receita"
			title="A ponte de receita abre no período padrão da tela."
		/>
	),
	dec: <Link to="/rede" />,
	fec: <Link to="/rede" />,
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
									link={LINKS[indicador]}
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
