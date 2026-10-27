import { Link } from "@tanstack/react-router";
import type { ReactElement } from "react";
import { KpiCard, type KpiDeltaProps } from "#/components/ui/kpi-card";
import {
	formatBRL,
	formatHoras,
	formatIndice,
	formatKWh,
	formatNumero,
	formatPeriodoCurto,
} from "#/lib/format";
import type { ComparacaoIndicadores, Indicador, ParPeriodos } from "../types";

type Definicao = {
	indicador: Indicador;
	label: string;
	format: (valor: number) => string;
	/** Direção que é melhora: define o verde e o vermelho da variação. */
	favorable: NonNullable<KpiDeltaProps["favorable"]>;
	hint: string;
	link?: (par: ParPeriodos | undefined) => ReactElement;
};

const GRUPOS: { id: string; titulo: string; cards: Definicao[] }[] = [
	{
		id: "comercial",
		titulo: "Comercial",
		cards: [
			{
				indicador: "receita_faturada",
				label: "Receita faturada",
				format: (valor) => formatBRL(valor, { compacto: true }),
				favorable: "up",
				hint: "Soma das faturas emitidas no período, com tributos.",
				link: (par) => (
					<Link
						to="/receita"
						search={{
							periodo_base: par?.periodo_base,
							periodo_atual: par?.periodo_atual,
						}}
					/>
				),
			},
			{
				indicador: "kwh_faturado",
				label: "Energia faturada",
				format: (valor) => formatKWh(valor, { compacto: true }),
				favorable: "up",
				hint: "kWh faturados no período, somados de todas as unidades consumidoras.",
			},
		],
	},
	{
		id: "rede",
		titulo: "Rede",
		cards: [
			{
				indicador: "dec",
				label: "DEC",
				format: formatHoras,
				favorable: "down",
				hint: "Duração equivalente de interrupção: horas sem energia, em média, por unidade consumidora no período.",
				link: () => <Link to="/rede" />,
			},
			{
				indicador: "fec",
				label: "FEC",
				format: formatIndice,
				favorable: "down",
				hint: "Frequência equivalente de interrupção: quantas vezes, em média, cada unidade consumidora ficou sem energia no período.",
				link: () => <Link to="/rede" />,
			},
		],
	},
	{
		id: "atendimento",
		titulo: "Atendimento",
		cards: [
			{
				indicador: "n_chamados",
				label: "Chamados",
				format: formatNumero,
				favorable: "down",
				hint: "Chamados de atendimento abertos no período.",
			},
			{
				indicador: "satisfacao_media",
				label: "Satisfação média",
				format: formatNumero,
				favorable: "up",
				hint: "Média das notas de 1 a 5 dos chamados avaliados no período; chamado sem nota fica fora.",
			},
		],
	},
];

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
						{grupo.cards.map((card) => {
							const valor = semDados
								? null
								: comparacao?.atual.valores[card.indicador];
							const variacao = comparacao?.variacao[card.indicador];
							return (
								<KpiCard
									key={card.indicador}
									label={card.label}
									value={valor}
									format={card.format}
									hint={card.hint}
									link={card.link?.(par)}
									highlight={card.indicador === "receita_faturada"}
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
													favorable: card.favorable,
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
