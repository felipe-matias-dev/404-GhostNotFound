import { InfoIcon } from "@phosphor-icons/react";
import type { ReactElement } from "react";
import { Button } from "#/components/ui/button";
import {
	SegmentedControl,
	type SegmentedOption,
} from "#/components/ui/segmented-control";
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
import { formatHoras, formatIndice, formatPeriodoCurto } from "#/lib/format";
import { serieDoAlimentador } from "../conversions";
import type { AlimentadorMensal, Criterio, Periodo } from "../types";

const INDICES: readonly SegmentedOption<Criterio>[] = [
	{ value: "dec", label: "DEC" },
	{ value: "fec", label: "FEC" },
];

const AJUDA =
	"DEC: duração equivalente, em horas, de interrupção por UC. FEC: frequência equivalente de interrupções por UC.";

export type AlimentadorSheetProps = {
	alimentador: string | undefined;
	periodo: Periodo | undefined;
	criterio: Criterio;
	fromRecorte: boolean;
	linhas: AlimentadorMensal[] | undefined;
	loading: boolean;
	refreshing: boolean;
	error: string | null;
	onRetry: () => void;
	onCriterioChange: (criterio: Criterio) => void;
	onClose: () => void;
};

/** Histórico global do alimentador: uma série mensal, com o índice escolhido só aqui. */
export function AlimentadorSheet({
	alimentador,
	periodo,
	criterio,
	fromRecorte,
	linhas,
	loading,
	refreshing,
	error,
	onRetry,
	onCriterioChange,
	onClose,
}: AlimentadorSheetProps): ReactElement {
	// Sem dados ainda, a série fica `undefined` para o gráfico mostrar o molde; converter as
	// linhas ausentes em período todo nulo faria um vazio falso antes da resposta.
	const serie =
		periodo && alimentador && linhas !== undefined
			? serieDoAlimentador(linhas, periodo, alimentador, criterio)
			: undefined;
	// Com o histórico na tela, a falha de atualização vira aviso; o erro nativo só sem série.
	const erroComDados = Boolean(error) && serie !== undefined;

	const nomeIndice = criterio === "dec" ? "DEC" : "FEC";
	const formatar = criterio === "dec" ? formatHoras : formatIndice;
	const codigo = alimentador ?? "";

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
						Histórico do alimentador inteiro, em todos os municípios e classes.
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

					{erroComDados && (
						<div
							role="alert"
							className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-danger/40 bg-danger-subtle p-3"
						>
							<p className="text-body text-danger">
								A atualização falhou. O histórico anterior continua exibido.
							</p>
							<Button variant="outline" size="sm" onClick={onRetry}>
								Tentar de novo
							</Button>
						</div>
					)}

					<TrendChart
						label={`Histórico de ${nomeIndice} do alimentador ${codigo}`}
						categories={serie?.categories}
						series={serie?.series}
						formatValue={formatar}
						categoryLabel="Competência"
						height={300}
						loading={Boolean(periodo) && loading}
						error={serie === undefined ? error : null}
						onRetry={onRetry}
						emptyMessage={
							periodo
								? "Sem histórico deste alimentador no período."
								: "Escolha um período para ver o histórico."
						}
						toolbar={
							<>
								{refreshing && (
									<output className="text-small text-text-muted">
										Atualizando…
									</output>
								)}
								<SegmentedControl
									label="Índice do histórico"
									value={criterio}
									onValueChange={onCriterioChange}
									options={INDICES}
								/>
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
									<TooltipContent>{AJUDA}</TooltipContent>
								</Tooltip>
							</>
						}
					/>
				</div>
			</SheetContent>
		</Sheet>
	);
}
