import {
	ArrowsLeftRightIcon,
	CalendarBlankIcon,
	CaretLeftIcon,
	CaretRightIcon,
	CheckIcon,
} from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
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
import { anoAnterior, type ParPeriodos } from "#/lib/filtros";

const MES = /^\d{4}-(0[1-9]|1[0-2])$/;

const mesValido = (mes: string) => MES.test(mes);

/**
 * Escolhe o período atual num calendário de meses (mês inicial, depois o final) e compara
 * com o mesmo trecho do ano anterior. Só habilita os trechos que a Gold gravou (DEC-028).
 */
export function PeriodoPicker({
	pares,
	par,
	onEscolher,
	erro,
	retry,
	carregando,
}: {
	pares: ParPeriodos[];
	par: ParPeriodos | undefined;
	onEscolher: (par: ParPeriodos) => void;
	erro?: boolean;
	retry?: () => void;
	carregando?: boolean;
}) {
	const [aberto, setAberto] = useState(false);
	const [manual, setManual] = useState(false);
	const [baseEditada, setBaseEditada] = useState(false);
	const [rascunho, setRascunho] = useState(["", "", "", ""]);
	const [ancora, setAncora] = useState<number | null>(null);
	const [sobre, setSobre] = useState<number | null>(null);
	const selecionado = par ? trechoDe(par.periodo_atual) : undefined;
	const [ano, setAno] = useState(() =>
		selecionado ? Math.floor(selecionado.fim / 12) : 0,
	);
	const valido =
		rascunho.every(mesValido) &&
		rascunho[0] <= rascunho[1] &&
		rascunho[2] <= rascunho[3];
	const incompleto = rascunho.some((mes) => mes !== "");

	const mudarMes = (indice: number, valor: string) => {
		if (indice >= 2) setBaseEditada(true);
		setRascunho((anterior) => {
			const proximo = [...anterior];
			proximo[indice] = valor;
			const [inicio, fim] = proximo;
			// Enquanto a base não foi editada à mão, ela espelha o atual um ano antes.
			if (
				indice < 2 &&
				!baseEditada &&
				mesValido(inicio) &&
				mesValido(fim) &&
				inicio <= fim
			) {
				const inicioBase = anoAnterior(inicio);
				const fimBase = anoAnterior(fim);
				if (inicioBase && fimBase) {
					proximo[2] = inicioBase;
					proximo[3] = fimBase;
				}
			}
			return proximo;
		});
	};

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

	useEffect(() => {
		if (!aberto || ano !== 0) return;
		const periodo = par?.periodo_atual ?? pares.at(-1)?.periodo_atual;
		if (!periodo) return;
		setAno(Math.floor(trechoDe(periodo).fim / 12));
		if (par && !manual) setRascunho([...par.periodo_atual.split("/"), ...par.periodo_base.split("/")]);
	}, [aberto, ano, manual, par, pares]);

	const abrir = (proximo: boolean) => {
		setAberto(proximo);
		setAncora(null);
		setSobre(null);
		if (!proximo) return;
		setManual(false);
		setBaseEditada(false);
		setRascunho(
			par
				? [...par.periodo_atual.split("/"), ...par.periodo_base.split("/")]
				: ["", "", "", ""],
		);
		const ultimo =
			selecionado ??
			(pares.length ? trechoDe(pares[pares.length - 1].periodo_atual) : undefined);
		if (ultimo) setAno(Math.floor(ultimo.fim / 12));
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
		: "Selecionar período";
	return (
		<Popover open={aberto} onOpenChange={abrir}>
			<PopoverTrigger
				aria-label={`Períodos comparados: ${atual}. Trocar`}
				className="flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-md border border-border-strong text-text-muted outline-none transition-colors hover:bg-hover hover:text-text focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover data-popup-open:text-text"
			>
				<CalendarBlankIcon aria-hidden className="size-4" />
			</PopoverTrigger>
			<PopoverContent
				align="end"
				className="w-[30rem] max-w-[calc(100vw-2rem)]"
			>
				{pares.length > 0 && !erro && !manual && <div className="flex">
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
												<CheckIcon aria-hidden className="size-3.5 shrink-0" />
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
				</div>}
				{carregando && pares.length === 0 && (
					<div className="p-3 text-small text-text-muted" role="status">
						Carregando períodos gravados…
					</div>
				)}
				{!carregando && (erro || pares.length === 0) && (
					<div className="p-3 text-small text-text-muted" role="status">
						{erro
							? "Não foi possível carregar os períodos gravados."
							: "Não há períodos gravados."}
						{erro && retry && (
							<button type="button" className="ml-2 underline" onClick={retry}>
								Tentar novamente
							</button>
						)}
					</div>
				)}
				<div className="border-border-strong border-t p-3">
					<button
						type="button"
						className="text-small underline"
						onClick={() => setManual(!manual)}
						aria-expanded={manual}
					>
						Personalizar
					</button>
					{manual && (
						<form
							className="mt-2 grid grid-cols-2 gap-2"
							onSubmit={(event) => {
								event.preventDefault();
								if (!valido) return;
								onEscolher({
									periodo_atual: `${rascunho[0]}/${rascunho[1]}`,
									periodo_base: `${rascunho[2]}/${rascunho[3]}`,
								});
								abrir(false);
							}}
						>
							{["Início atual", "Fim atual", "Início base", "Fim base"].map(
								(rotulo, indice) => (
									<label
										key={rotulo}
										className="flex flex-col gap-1 text-small text-text-muted"
									>
										{rotulo}
										<input
											type="month"
											required
											value={rascunho[indice]}
											onChange={(event) => mudarMes(indice, event.target.value)}
											className="min-w-0 rounded-md border border-border-strong bg-surface px-2 py-1 text-text"
										/>
									</label>
								),
							)}
							{incompleto && !valido && (
								<p className="col-span-2 text-small text-text-muted" role="status">
									Preencha os quatro meses, com o início antes do fim em cada
									intervalo.
								</p>
							)}
							<button
								type="submit"
								disabled={!valido}
								className="col-span-2 rounded-md border border-border-strong px-2 py-1 text-small disabled:opacity-50"
							>
								Aplicar
							</button>
						</form>
					)}
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
										"cursor-pointer rounded-sm border px-1.5 py-0.5 outline-none focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50",
										b === par.periodo_base
											? "border-border-strong bg-pressed text-text"
											: "border-transparent text-text-muted hover:bg-hover hover:text-text",
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
