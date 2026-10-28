import {
	ArrowsLeftRightIcon,
	CalendarBlankIcon,
	CaretDownIcon,
	CaretLeftIcon,
	CaretRightIcon,
} from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "#/components/ui/popover";
import { formatCompetencia, formatPeriodoCurto, MESES } from "#/lib/format";
import { cn } from "#/lib/utils";
import {
	basesDoMes,
	mesDoPeriodo,
	parDoMes,
	periodoDoMes,
	relacaoDoPar,
} from "../conversions";
import type { ParPeriodos } from "../types";

const competenciaDe = (ano: number, indice: number) =>
	`${ano}-${String(indice + 1).padStart(2, "0")}`;

/**
 * Escolhe o mês atual num calendário e a base logo abaixo: o mesmo mês do ano anterior ou o
 * mês anterior. Só habilita os meses que têm base na série. A faixa é mensal; o resumo de
 * receita e energia usa as janelas de 12 meses, independentemente deste seletor.
 */
export function ComparacaoPicker({
	competencias,
	par,
	onEscolher,
	semPeriodos,
}: {
	competencias: string[];
	par: ParPeriodos | undefined;
	onEscolher: (par: ParPeriodos) => void;
	/** A série falhou ou não tem dois meses: nada a escolher, e não "carregando". */
	semPeriodos: boolean;
}) {
	const [aberto, setAberto] = useState(false);
	const atual = par ? mesDoPeriodo(par.periodo_atual) : undefined;
	const anoAtual = atual ? Number(atual.slice(0, 4)) : 0;
	const [ano, setAno] = useState(anoAtual);

	const { comBase, anoMin, anoMax } = useMemo(() => {
		const anos = competencias.map((c) => Number(c.slice(0, 4)));
		return {
			comBase: new Set(
				competencias.filter((c) => basesDoMes(competencias, c).length > 0),
			),
			anoMin: Math.min(...anos),
			anoMax: Math.max(...anos),
		};
	}, [competencias]);
	const bases = atual ? basesDoMes(competencias, atual) : [];
	const relacao = par ? relacaoDoPar(par) : undefined;

	const abrir = (proximo: boolean) => {
		setAberto(proximo);
		if (proximo && atual) setAno(anoAtual);
	};
	const escolherMes = (competencia: string) => {
		const escolhido = parDoMes(competencias, competencia, relacao);
		if (escolhido) onEscolher(escolhido);
		abrir(false);
	};

	const rotulo = par
		? `${formatPeriodoCurto(par.periodo_atual)} vs ${formatPeriodoCurto(par.periodo_base)}`
		: semPeriodos
			? "Sem períodos"
			: "Carregando…";
	return (
		<Popover open={aberto} onOpenChange={abrir}>
			<PopoverTrigger
				aria-label={`Períodos comparados: ${rotulo}. Trocar`}
				disabled={!par}
				className="flex h-7 min-w-0 cursor-pointer items-center gap-1.5 rounded-md border border-border-strong px-2 text-small text-text-muted outline-none transition-colors hover:bg-hover hover:text-text focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 disabled:pointer-events-none disabled:text-text-disabled data-popup-open:bg-hover data-popup-open:text-text"
			>
				<CalendarBlankIcon aria-hidden className="size-3.5 shrink-0" />
				<span className="truncate">{rotulo}</span>
				<CaretDownIcon aria-hidden className="size-3 shrink-0" />
			</PopoverTrigger>
			<PopoverContent align="end" className="w-72 max-w-[calc(100vw-2rem)]">
				<div className="flex flex-col gap-2 p-3">
					<div className="flex items-center justify-between">
						<button
							type="button"
							aria-label="Ano anterior"
							disabled={ano <= anoMin}
							onClick={() => setAno(ano - 1)}
							className="flex size-7 cursor-pointer items-center justify-center rounded-md text-text-muted outline-none hover:bg-hover hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50 disabled:pointer-events-none disabled:text-text-disabled"
						>
							<CaretLeftIcon aria-hidden className="size-3.5" />
						</button>
						<span className="font-medium text-body tabular-nums">{ano}</span>
						<button
							type="button"
							aria-label="Próximo ano"
							disabled={ano >= anoMax}
							onClick={() => setAno(ano + 1)}
							className="flex size-7 cursor-pointer items-center justify-center rounded-md text-text-muted outline-none hover:bg-hover hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50 disabled:pointer-events-none disabled:text-text-disabled"
						>
							<CaretRightIcon aria-hidden className="size-3.5" />
						</button>
					</div>

					<div className="grid grid-cols-3 gap-1">
						{MESES.map((nome, indice) => {
							const competencia = competenciaDe(ano, indice);
							const escolhido = competencia === atual;
							return (
								<button
									key={nome}
									type="button"
									disabled={!comBase.has(competencia)}
									aria-pressed={escolhido}
									aria-label={formatCompetencia(competencia)}
									onClick={() => escolherMes(competencia)}
									className={cn(
										"h-8 cursor-pointer rounded-md text-body outline-none transition-colors focus-visible:ring-3 focus-visible:ring-focus-ring/50 disabled:pointer-events-none disabled:text-text-disabled",
										escolhido
											? "bg-accent font-medium text-on-accent"
											: "text-text hover:bg-hover",
									)}
								>
									{nome}
								</button>
							);
						})}
					</div>

					<p className="text-small text-text-muted">Escolha o mês atual.</p>
				</div>

				{par && bases.length > 0 && (
					<div className="flex flex-wrap items-center gap-2 border-border-strong border-t px-3 py-2 text-small">
						<ArrowsLeftRightIcon
							aria-hidden
							className="size-3.5 text-text-muted"
						/>
						<span className="text-text-muted">Comparado com</span>
						{bases.map((base) => {
							const periodo = periodoDoMes(base.competencia);
							const ativa = periodo === par.periodo_base;
							return (
								<button
									key={base.relacao}
									type="button"
									aria-pressed={ativa}
									onClick={() =>
										onEscolher({
											periodo_base: periodo,
											periodo_atual: par.periodo_atual,
										})
									}
									className={cn(
										"cursor-pointer rounded-sm border px-1.5 py-0.5 outline-none focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50",
										ativa
											? "border-border-strong bg-pressed text-text"
											: "border-transparent text-text-muted hover:bg-hover hover:text-text",
									)}
								>
									{formatPeriodoCurto(periodo)}
								</button>
							);
						})}
					</div>
				)}
			</PopoverContent>
		</Popover>
	);
}
