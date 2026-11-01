import { InfoIcon } from "@phosphor-icons/react";
import type { ReactElement, ReactNode } from "react";
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
} from "../conversions";
import { INDICADORES_REDE } from "../indicadores";
import type { AlimentadorMensal, Periodo, ReferenciaMensal } from "../types";

const AJUDA = `DEC: ${INDICADORES_REDE.dec.hint} FEC: ${INDICADORES_REDE.fec.hint} A linha cinza é a empresa inteira no mesmo mês.`;

export type AlimentadorSheetProps = {
	alimentador: string | undefined;
	periodo: Periodo | undefined;
	fromRecorte: boolean;
	linhas: AlimentadorMensal[] | undefined;
	/** DEC e FEC mensais da empresa; sem eles, o gráfico mostra só o alimentador. */
	empresa: ReferenciaMensal[] | undefined;
	loading: boolean;
	refreshing: boolean;
	/** A consulta do histórico falhou; com histórico na tela, vira aviso de atualização. */
	failed: boolean;
	onRetry: () => void;
	onClose: () => void;
};

/** O que aconteceu no mês sob o cursor, além do índice: as contagens que formam o DEC e o FEC. */
const rodape = (historico: HistoricoAlimentador) => (indice: number) => {
	const mes = historico.meses[indice];
	if (!mes) return "Sem dado do alimentador neste mês.";
	return `${formatHoras(mes.horas_interrompidas)} interrompidas · ${formatNumero(mes.n_interrupcoes)} interrupções · ${formatNumero(mes.n_uc)} UCs`;
};

/** Histórico global do alimentador: DEC e FEC mensais, com a empresa como referência. */
export function AlimentadorSheet({
	alimentador,
	periodo,
	fromRecorte,
	linhas,
	empresa,
	loading,
	refreshing,
	failed,
	onRetry,
	onClose,
}: AlimentadorSheetProps): ReactElement {
	// Sem dados ainda, o histórico fica `undefined` para o gráfico mostrar o molde; converter as
	// linhas ausentes em período todo nulo faria um vazio falso antes da resposta.
	const periodoLongo = periodo !== undefined && periodoExcedeGrafico(periodo);
	const historico =
		periodo && !periodoLongo && alimentador && linhas !== undefined
			? historicoDoAlimentador(linhas, periodo, alimentador, empresa)
			: undefined;
	const codigo = alimentador ?? "";

	const grafico = (
		indice: "dec" | "fec",
		formatar: (valor: number) => string,
		toolbar?: ReactNode,
	) => (
		<TrendChart
			label={`Histórico de ${indice.toUpperCase()} do alimentador ${codigo}`}
			categories={historico?.categories}
			series={historico?.series[indice]}
			formatValue={formatar}
			categoryLabel="Competência"
			height={200}
			endLabels={Boolean(empresa)}
			tooltipFooter={historico ? rodape(historico) : undefined}
			summary={
				<span className="text-small font-medium text-text">
					{indice.toUpperCase()}
				</span>
			}
			toolbar={toolbar}
			loading={Boolean(periodo) && loading}
			emptyMessage={
				periodo
					? "Sem histórico deste alimentador no período."
					: "Escolha um período para ver o histórico."
			}
		/>
	);

	return (
		<Sheet
			open={Boolean(alimentador)}
			onOpenChange={(aberto) => {
				if (!aberto) onClose();
			}}
		>
			<SheetContent
				side="right"
				className="data-[side=right]:w-full data-[side=right]:sm:max-w-2xl"
			>
				<SheetHeader className="pr-12">
					<SheetTitle>Alimentador {codigo}</SheetTitle>
					<SheetDescription>
						Histórico do alimentador inteiro, em todos os municípios e classes,
						com a empresa como referência.
					</SheetDescription>
				</SheetHeader>

				<div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 pb-4">
					{(periodo || fromRecorte) && (
						<div className="flex flex-col gap-1 text-small text-text-muted">
							{periodo && (
								<p>
									Período:{" "}
									{formatPeriodoCurto(`${periodo.inicio}/${periodo.fim}`)}
								</p>
							)}
							{fromRecorte && (
								<p>
									Os índices do recorte na tabela podem diferir deste histórico.
								</p>
							)}
						</div>
					)}

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
							O gráfico comporta até {MAX_MESES_GRAFICO} meses. Escolha um
							período menor para ver o histórico.
						</output>
					) : (
						(historico || !failed) && (
							<>
								{grafico(
									"dec",
									formatHoras,
									<>
										{refreshing && (
											<output className="text-small text-text-muted">
												Atualizando…
											</output>
										)}
										<Tooltip>
											<TooltipTrigger
												delay={0}
												render={
													<button
														type="button"
														aria-label="Sobre os índices DEC e FEC"
														className="grid size-6 shrink-0 place-items-center rounded-sm text-text-muted outline-none transition-colors hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50"
													/>
												}
											>
												<InfoIcon aria-hidden className="size-3.5" />
											</TooltipTrigger>
											<TooltipContent className="max-w-sm">
												{AJUDA}
											</TooltipContent>
										</Tooltip>
									</>,
								)}
								{grafico("fec", formatIndice)}
							</>
						)
					)}
				</div>
			</SheetContent>
		</Sheet>
	);
}
