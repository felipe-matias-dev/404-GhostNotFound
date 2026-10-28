import { CaretDownIcon, ChartLineIcon } from "@phosphor-icons/react";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuLabel,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "#/components/ui/dropdown-menu";
import { KpiDelta } from "#/components/ui/kpi-card";
import { SegmentedControl } from "#/components/ui/segmented-control";
import { TrendChart } from "#/components/ui/trend-chart";
import { formatCompetencia } from "#/lib/format";
import {
	INDICADORES,
	marcadores,
	type VisaoTendencia,
	variacaoNoPonto,
} from "../conversions";
import { useTendencia } from "../hooks/use-indicadores";
import { DEFINICOES, GRUPOS } from "../indicadores";
import type { Indicador, ParPeriodos } from "../types";

const VISOES = [
	{ value: "mes", label: "Mês a mês" },
	{ value: "ano", label: "Ano a ano" },
] as const;

function IndicadorPicker({
	indicador,
	onEscolher,
}: {
	indicador: Indicador;
	onEscolher: (indicador: Indicador) => void;
}) {
	return (
		<DropdownMenu>
			<DropdownMenuTrigger
				aria-label={`Indicador do gráfico: ${DEFINICOES[indicador].label}. Trocar`}
				className="flex h-7 min-w-0 cursor-pointer items-center gap-1.5 rounded-md border border-border px-2 text-small text-text-muted outline-none transition-colors hover:bg-hover hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover data-popup-open:text-text"
			>
				<ChartLineIcon aria-hidden className="size-3.5 shrink-0" />
				<span className="truncate">{DEFINICOES[indicador].label}</span>
				<CaretDownIcon aria-hidden className="size-3 shrink-0" />
			</DropdownMenuTrigger>
			<DropdownMenuContent align="end">
				<DropdownMenuRadioGroup
					value={indicador}
					onValueChange={(proximo: string) => {
						const escolhido = INDICADORES.find((i) => i === proximo);
						if (escolhido) onEscolher(escolhido);
					}}
				>
					{GRUPOS.map((grupo, i) => (
						<DropdownMenuGroup key={grupo.id}>
							{i > 0 ? <DropdownMenuSeparator /> : null}
							<DropdownMenuLabel>{grupo.titulo}</DropdownMenuLabel>
							{grupo.indicadores.map((item) => (
								<DropdownMenuRadioItem key={item} value={item} closeOnClick>
									{DEFINICOES[item].label}
								</DropdownMenuRadioItem>
							))}
						</DropdownMenuGroup>
					))}
				</DropdownMenuRadioGroup>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}

export function TendenciaPainel({
	indicador,
	visao,
	par,
	onIndicador,
	onVisao,
}: {
	indicador: Indicador;
	visao: VisaoTendencia;
	par: ParPeriodos | undefined;
	onIndicador: (indicador: Indicador) => void;
	onVisao: (visao: VisaoTendencia) => void;
}) {
	const definicao = DEFINICOES[indicador];
	const serie = useTendencia(indicador, visao, definicao.label);
	const dados = serie.data;
	const primeira = dados?.categories[0]?.key;
	const ultima = dados?.categories.at(-1)?.key;
	const resumo = !dados
		? null
		: visao === "mes"
			? `${formatCompetencia(primeira)} a ${formatCompetencia(ultima)}`
			: "Um ano por linha; o mais recente em destaque.";

	return (
		<section aria-labelledby="tendencia" className="flex flex-1 flex-col gap-3">
			<h2 id="tendencia" className="text-heading">
				Tendência
			</h2>
			<TrendChart
				label={`${definicao.label}, ${visao === "mes" ? "mês a mês" : "ano a ano"}`}
				categories={dados?.categories}
				series={dados?.series}
				formatValue={definicao.format}
				categoryLabel={visao === "mes" ? "Competência" : "Mês"}
				markers={marcadores(par, visao)}
				summary={resumo}
				toolbar={
					<>
						<IndicadorPicker indicador={indicador} onEscolher={onIndicador} />
						<SegmentedControl
							label="Visão do gráfico"
							value={visao}
							onValueChange={onVisao}
							options={VISOES}
						/>
					</>
				}
				tooltipFooter={(indice) => {
					const ponto = dados ? variacaoNoPonto(dados, indice) : undefined;
					return ponto ? (
						<KpiDelta
							value={ponto.valor}
							favorable={definicao.favorable}
							comparison={`vs. ${ponto.base}`}
						/>
					) : (
						<p className="text-text-muted">Sem base para comparar.</p>
					);
				}}
				loading={serie.isPending}
				error={
					serie.isError && !serie.data
						? "Não foi possível carregar a série."
						: null
				}
				onRetry={() => serie.refetch()}
				emptyMessage="Sem meses carregados."
				height="fill"
				className="flex-1"
			/>
		</section>
	);
}
