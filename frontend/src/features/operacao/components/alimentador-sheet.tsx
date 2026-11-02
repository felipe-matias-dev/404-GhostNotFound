import { InfoIcon } from "@phosphor-icons/react";
import type { ReactElement } from "react";
import { Button } from "#/components/ui/button";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "#/components/ui/sheet";
import {
	Tooltip,
	TooltipContent,
	TooltipTrigger,
} from "#/components/ui/tooltip";
import { TrendChart } from "#/components/ui/trend-chart";
import {
	formatHoras,
	formatIndice,
	formatNumero,
	formatPeriodoCurto,
} from "#/lib/format";
import {
	type HistoricoAlimentador,
	historicoDoAlimentador,
	MAX_MESES_GRAFICO,
	periodoExcedeGrafico,
	type ReferenciaHistorico,
} from "../conversions";
import { useResumoOcorrencias } from "../hooks/use-continuidade";
import { INDICADORES_REDE } from "../indicadores";
import type { ContinuidadeMensal, Periodo, Recorte } from "../types";
import {
	CausasAlimentador,
	DuracaoAlimentador,
	ResumoAlimentador,
	UcsMaisAtingidas,
} from "./painel-alimentador";

/** O que o painel do alimentador mostra: os dados vêm da página da Rede. */
export type DadosAlimentador = {
	alimentador: string | undefined;
	periodo: Periodo | undefined;
	/** O recorte da tela: o alimentador é mostrado dentro dele. */
	recorte: Recorte;
	/** Nome do recorte ("Recife · Residencial (B1)"); sem recorte, a empresa. */
	nomeRecorte: string | undefined;
	/** A série do alimentador dentro do recorte. */
	linhas: ContinuidadeMensal[] | undefined;
	/** A série do recorte inteiro; sem ela, o gráfico mostra só o alimentador. */
	referencia: ContinuidadeMensal[] | undefined;
	loading: boolean;
	refreshing: boolean;
	/** A consulta do histórico falhou; com histórico na tela, vira aviso de atualização. */
	failed: boolean;
	onRetry: () => void;
};

/** O que aconteceu no mês sob o cursor, além do índice: as contagens que formam o DEC e o FEC. */
const rodape = (historico: HistoricoAlimentador) => (indice: number) => {
	const mes = historico.meses[indice];
	if (!mes) return "Sem dado do alimentador neste mês e recorte.";
	return `${formatHoras(mes.horas_interrompidas)} interrompidas · ${formatNumero(mes.n_interrupcoes)} interrupções · ${formatNumero(mes.n_uc)} UCs`;
};

/** O recorte (ou o alimentador inteiro) e o período: o subtítulo do painel. */
const contexto = (
	nomeRecorte: string | undefined,
	periodo: Periodo | undefined,
) =>
	`${nomeRecorte ?? "Alimentador inteiro"}${periodo ? ` · ${formatPeriodoCurto(`${periodo.inicio}/${periodo.fim}`)}` : ""}`;

/**
 * O alimentador no recorte, em blocos: quanto sofreu no período, DEC e FEC mês a mês contra o
 * recorte inteiro, por que cai, quanto dura cada falta e quem mais sofreu.
 */
function BlocosAlimentador({
	alimentador,
	periodo,
	recorte,
	nomeRecorte,
	linhas,
	referencia,
	loading,
	refreshing,
	failed,
	onRetry,
}: DadosAlimentador & { alimentador: string }): ReactElement {
	// Sem dados ainda, o histórico fica `undefined` para o gráfico mostrar o molde; converter as
	// linhas ausentes em período todo nulo faria um vazio falso antes da resposta.
	const periodoLongo = periodo !== undefined && periodoExcedeGrafico(periodo);
	const comparacao: ReferenciaHistorico | undefined = referencia && {
		rotulo: nomeRecorte ?? "Empresa",
		rotuloCurto: nomeRecorte ? "recorte" : "empresa",
		linhas: referencia,
	};
	const historico =
		periodo && !periodoLongo && linhas !== undefined
			? historicoDoAlimentador(linhas, periodo, alimentador, comparacao)
			: undefined;
	const daReferencia = nomeRecorte ? `o recorte ${nomeRecorte}` : "a empresa";
	const resumo = useResumoOcorrencias(periodo, recorte, alimentador);
	const comOcorrencias = (resumo.data?.total.n_interrupcoes ?? 0) > 0;

	// Cada gráfico explica o próprio índice no (i); o "Atualizando…" fica só no primeiro.
	const grafico = (
		indice: "dec" | "fec",
		formatar: (valor: number) => string,
		atualizando = false,
	) => (
		<TrendChart
			label={`Histórico de ${indice.toUpperCase()} do alimentador ${alimentador}`}
			categories={historico?.categories}
			series={historico?.series[indice]}
			formatValue={formatar}
			categoryLabel="Competência"
			height={200}
			endLabels={Boolean(referencia)}
			tooltipFooter={historico ? rodape(historico) : undefined}
			summary={
				<span className="flex flex-col">
					<span className="text-heading text-text">
						{indice.toUpperCase()} por mês
					</span>
					<span className="text-small text-text-muted">
						Em cinza, {daReferencia}
					</span>
				</span>
			}
			toolbar={
				<>
					{atualizando && (
						<output className="text-small text-text-muted">Atualizando…</output>
					)}
					<Tooltip>
						<TooltipTrigger
							delay={0}
							render={
								<button
									type="button"
									aria-label={`Sobre o ${indice.toUpperCase()}`}
									className="grid size-6 shrink-0 place-items-center rounded-sm text-text-muted outline-none transition-colors hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50"
								/>
							}
						>
							<InfoIcon aria-hidden className="size-3.5" />
						</TooltipTrigger>
						<TooltipContent className="max-w-sm">
							{INDICADORES_REDE[indice].hint} A linha cinza é {daReferencia} no
							mesmo mês.
						</TooltipContent>
					</Tooltip>
				</>
			}
			loading={Boolean(periodo) && loading}
			emptyMessage={
				periodo
					? "Sem histórico deste alimentador no período e recorte."
					: "Escolha um período para ver o histórico."
			}
		/>
	);

	return (
		<div className="grid gap-3">
			{periodo && <ResumoAlimentador resumo={resumo} />}

			{failed && (
				<div
					role="alert"
					className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-danger/40 bg-danger-subtle p-3"
				>
					<p className="text-body text-danger">
						{historico
							? "A atualização falhou. O histórico anterior continua exibido."
							: "Não foi possível carregar o histórico do alimentador."}
					</p>
					<Button variant="outline" size="sm" onClick={onRetry}>
						Tentar de novo
					</Button>
				</div>
			)}

			{periodoLongo ? (
				<output className="text-body text-text-muted">
					O gráfico comporta até {MAX_MESES_GRAFICO} meses. Escolha um período
					menor para ver o histórico.
				</output>
			) : (
				(historico || !failed) && (
					<>
						{grafico("dec", formatHoras, refreshing)}
						{grafico("fec", formatIndice)}
					</>
				)
			)}

			{periodo && resumo.data && comOcorrencias && (
				<>
					<CausasAlimentador resumo={resumo.data} />
					<DuracaoAlimentador resumo={resumo.data} />
					<UcsMaisAtingidas
						alimentador={alimentador}
						periodo={periodo}
						recorte={recorte}
					/>
				</>
			)}
		</div>
	);
}

/** O alimentador num painel à direita, sobre a tabela. */
export function AlimentadorSheet({
	aberto,
	onClose,
	...dados
}: DadosAlimentador & {
	aberto: boolean;
	onClose: () => void;
}): ReactElement {
	const codigo = dados.alimentador ?? "";
	return (
		<Sheet
			open={aberto}
			onOpenChange={(proximo) => {
				if (!proximo) onClose();
			}}
		>
			<SheetContent
				side="right"
				className="data-[side=right]:w-full data-[side=right]:sm:max-w-2xl"
			>
				<SheetHeader className="pr-12">
					<SheetTitle>Alimentador {codigo}</SheetTitle>
					<SheetDescription>
						{contexto(dados.nomeRecorte, dados.periodo)}
					</SheetDescription>
				</SheetHeader>
				<div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4">
					{dados.alimentador && (
						<BlocosAlimentador {...dados} alimentador={dados.alimentador} />
					)}
				</div>
			</SheetContent>
		</Sheet>
	);
}
