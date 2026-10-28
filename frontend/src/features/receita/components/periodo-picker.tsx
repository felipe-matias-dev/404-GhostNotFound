import {
	ArrowsLeftRightIcon,
	CalendarBlankIcon,
	CaretDownIcon,
	CaretLeftIcon,
	CaretRightIcon,
	CheckIcon,
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
	atalhos,
	basesDoAtual,
	competenciaDe,
	parDoAtual,
	periodoDe,
	trechoDe,
} from "../conversions";
import type { ParPeriodos } from "../types";

/**
 * Escolhe o período atual num calendário de meses (mês inicial, depois o final) e compara
 * com o mesmo trecho do ano anterior. Só habilita os trechos que a Gold gravou (DEC-028).
 */
export function PeriodoPicker({
	pares,
	par,
	onEscolher,
}: {
	pares: ParPeriodos[];
	par: ParPeriodos | undefined;
	onEscolher: (par: ParPeriodos) => void;
}) {
	const [aberto, setAberto] = useState(false);
	const [ancora, setAncora] = useState<number | null>(null);
	const [sobre, setSobre] = useState<number | null>(null);
	const selecionado = par ? trechoDe(par.periodo_atual) : undefined;
	const [ano, setAno] = useState(() =>
		selecionado ? Math.floor(selecionado.fim / 12) : 0,
	);

	const { atuais, inicios, anoMin, anoMax } = useMemo(() => {
		const atuais = new Set(pares.map((p) => p.periodo_atual));
		const trechos = [...atuais].map(trechoDe);
		return {
			atuais,
			inicios: new Set(trechos.map((t) => t.inicio)),
			anoMin: Math.min(...trechos.map((t) => Math.floor(t.inicio / 12))),
			anoMax: Math.max(...trechos.map((t) => Math.floor(t.fim / 12))),
		};
	}, [pares]);
	const listaAtalhos = useMemo(() => atalhos(pares), [pares]);
	const bases = par ? basesDoAtual(pares, par.periodo_atual) : [];

	const abrir = (proximo: boolean) => {
		setAberto(proximo);
		setAncora(null);
		setSobre(null);
		if (proximo && selecionado) setAno(Math.floor(selecionado.fim / 12));
	};
	const aplicar = (atual: string, base?: string) => {
		const escolhido = parDoAtual(pares, atual, base);
		if (escolhido) onEscolher(escolhido);
	};

	const clicar = (mes: number) => {
		if (ancora === null) {
			setAncora(mes);
			return;
		}
		aplicar(periodoDe(ancora, mes));
		abrir(false);
	};

	// Com o mês inicial marcado, a faixa acompanha o ponteiro; sem ele, mostra o escolhido.
	const faixa =
		ancora !== null
			? {
					inicio: Math.min(ancora, sobre ?? ancora),
					fim: Math.max(ancora, sobre ?? ancora),
				}
			: selecionado;

	const atual = par
		? `${formatPeriodoCurto(par.periodo_atual)} vs ${formatPeriodoCurto(par.periodo_base)}`
		: "Carregando…";
	return (
		<Popover open={aberto} onOpenChange={abrir}>
			<PopoverTrigger
				aria-label={`Períodos comparados: ${atual}. Trocar`}
				disabled={!par}
				className="flex h-7 min-w-0 cursor-pointer items-center gap-1.5 rounded-md border border-border px-2 text-small text-text-muted outline-none transition-colors hover:bg-hover hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover data-popup-open:text-text"
			>
				<CalendarBlankIcon aria-hidden className="size-3.5 shrink-0" />
				<span className="truncate">{atual}</span>
				<CaretDownIcon aria-hidden className="size-3 shrink-0" />
			</PopoverTrigger>
			<PopoverContent
				align="end"
				className="w-[30rem] max-w-[calc(100vw-2rem)]"
			>
				<div className="flex">
					{listaAtalhos.length > 0 && (
						<ul className="flex w-44 shrink-0 flex-col gap-0.5 border-border-strong border-r p-1.5">
							{listaAtalhos.map((a) => {
								const ativo = a.atual === par?.periodo_atual;
								return (
									<li key={a.atual}>
										<button
											type="button"
											onClick={() => {
												aplicar(a.atual);
												abrir(false);
											}}
											className={cn(
												"flex w-full cursor-pointer items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-left text-body outline-none hover:bg-hover focus-visible:bg-hover",
												ativo ? "text-text" : "text-text-muted",
											)}
										>
											<span className="flex min-w-0 flex-col">
												<span className="truncate">{a.rotulo}</span>
												<span className="text-small text-text-muted">
													{formatPeriodoCurto(a.atual)}
												</span>
											</span>
											{ativo && (
												<CheckIcon
													aria-hidden
													className="size-3.5 shrink-0 text-accent-text"
												/>
											)}
										</button>
									</li>
								);
							})}
						</ul>
					)}

					<div className="flex min-w-0 flex-1 flex-col gap-2 p-3">
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

						<div
							className="grid grid-cols-3 gap-y-1"
							onPointerLeave={() => setSobre(null)}
						>
							{MESES.map((nome, i) => {
								const mes = ano * 12 + i;
								const ok =
									ancora === null
										? inicios.has(mes)
										: atuais.has(periodoDe(ancora, mes));
								const dentro =
									faixa !== undefined &&
									mes >= faixa.inicio &&
									mes <= faixa.fim;
								const ponta =
									dentro && (mes === faixa.inicio || mes === faixa.fim);
								return (
									<button
										key={nome}
										type="button"
										disabled={!ok}
										aria-pressed={dentro}
										aria-label={formatCompetencia(competenciaDe(mes))}
										onClick={() => clicar(mes)}
										onPointerEnter={() => setSobre(mes)}
										onFocus={() => setSobre(mes)}
										className={cn(
											"h-8 cursor-pointer text-body outline-none transition-colors focus-visible:ring-3 focus-visible:ring-focus-ring/50 disabled:pointer-events-none disabled:text-text-disabled",
											dentro
												? "bg-accent-subtle text-accent-text"
												: "rounded-md text-text hover:bg-hover",
											dentro && mes === faixa.inicio && "rounded-l-md",
											dentro && mes === faixa.fim && "rounded-r-md",
											dentro && i % 3 === 0 && "rounded-l-md",
											dentro && i % 3 === 2 && "rounded-r-md",
											ponta && "bg-accent font-medium text-on-accent",
										)}
									>
										{nome}
									</button>
								);
							})}
						</div>

						<p className="text-small text-text-muted">
							{ancora === null
								? "Clique no mês inicial e depois no final."
								: `De ${formatCompetencia(competenciaDe(ancora))}: escolha o mês final.`}
						</p>
					</div>
				</div>

				{par && (
					<div className="flex flex-wrap items-center gap-2 border-border-strong border-t px-3 py-2 text-small">
						<ArrowsLeftRightIcon
							aria-hidden
							className="size-3.5 text-text-muted"
						/>
						<span className="text-text-muted">Comparado com</span>
						{bases.length > 1 ? (
							bases.map((b) => (
								<button
									key={b}
									type="button"
									aria-pressed={b === par.periodo_base}
									onClick={() => aplicar(par.periodo_atual, b)}
									className={cn(
										"cursor-pointer rounded-sm border px-1.5 py-0.5 outline-none focus-visible:ring-3 focus-visible:ring-focus-ring/50",
										b === par.periodo_base
											? "border-accent bg-accent-subtle text-accent-text"
											: "border-border-strong text-text-muted hover:bg-hover hover:text-text",
									)}
								>
									{formatPeriodoCurto(b)}
								</button>
							))
						) : (
							<span className="text-text">
								{formatPeriodoCurto(par.periodo_base)}
							</span>
						)}
					</div>
				)}
			</PopoverContent>
		</Popover>
	);
}
