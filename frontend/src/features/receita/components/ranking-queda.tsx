import { XIcon } from "@phosphor-icons/react";
import { useState } from "react";
import { Button } from "#/components/ui/button";
import { formatBRL, formatPct } from "#/lib/format";
import { cn } from "#/lib/utils";
import {
	EFEITO_ROTULO,
	type Efeito,
	filtroAoAbrir,
	type Medida,
	type Nivel,
	nivelDoFiltro,
	rankingDaQueda,
} from "../conversions";
import { useDecomposicao } from "../hooks/use-decomposicao";
import type { DecomposicaoLinha, ParPeriodos, Recorte } from "../types";

const MEDIDAS: { id: Medida; rotulo: string; nome: string }[] = [
	{ id: "brl", rotulo: "R$", nome: "Ranquear pelo valor em reais" },
	{ id: "pct", rotulo: "%", nome: "Ranquear pelo percentual da receita base" },
];

const LIMITE = 5;

const PLURAL: Record<Nivel, string> = {
	municipio: "municípios",
	bairro: "bairros",
	classe: "classes",
};

const NENHUM: Record<Nivel, string> = {
	municipio: "Nenhum município",
	bairro: "Nenhum bairro",
	classe: "Nenhuma classe",
};

const POR: Record<Efeito, string> = {
	variacao: "",
	tarifa: " pela tarifa",
	bandeira: " pela bandeira",
	volume: " por volume",
	mix: " por mix",
};

export function RankingQueda({
	par,
	recorte,
	efeito,
	onEfeito,
	onAbrir,
	onDestaque,
}: {
	par: ParPeriodos | undefined;
	recorte: Recorte;
	/** Causa escolhida na ponte; `variacao` ranqueia pela variação total. */
	efeito: Efeito;
	onEfeito: (efeito: Efeito) => void;
	onAbrir: (proximo: Recorte) => void;
	onDestaque?: (linha: DecomposicaoLinha | null) => void;
}) {
	const { data, isPending, isPlaceholderData, isError } = useDecomposicao(
		par,
		recorte,
	);
	const nivel = data?.[0]?.nivel ?? nivelDoFiltro(recorte);
	const navegavel = nivel !== "classe" && !isPlaceholderData;
	// Em R$ o maior segmento domina; em %, aparece quem caiu mais em proporção.
	const [medida, setMedida] = useState<Medida>("brl");
	const ranking = data
		? rankingDaQueda(data, efeito, medida, LIMITE)
		: undefined;

	// A tabela logo abaixo já mostra erro (com nova tentativa) e o recorte vazio.
	if (isError || data?.length === 0) return null;

	// Em %, segmento sem receita base fica de fora; se só há desses (ex.: classe nova no
	// bairro), a seção continua, com o botão para voltar ao R$.
	const semBase = ranking?.total === 0;
	const leitura = semBase
		? "Sem receita base para comparar em %: veja em R$."
		: ranking?.houveQueda
			? `${ranking.quedas} de ${ranking.total} ${PLURAL[nivel]} ${
					ranking.quedas === 1 ? "perdeu" : "perderam"
				} receita${POR[efeito]}.`
			: ranking &&
				`${NENHUM[nivel]} perdeu receita${POR[efeito]}: abaixo, quem subiu menos.`;

	return (
		<section
			aria-labelledby="ranking-titulo"
			aria-busy={isPending || isPlaceholderData}
			className="@container flex flex-col gap-3 rounded-lg border border-border bg-surface-1 px-4 py-3"
		>
			<div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
				<div className="flex min-w-0 flex-col gap-0.5">
					<h3 id="ranking-titulo" className="text-body font-medium text-text">
						{ranking && !semBase && !ranking.houveQueda
							? "Menores altas"
							: "Maiores contribuintes da queda"}
						{efeito !== "variacao" && (
							<span className="text-text-muted">
								{" "}
								· {EFEITO_ROTULO[efeito].toLowerCase()}
							</span>
						)}
					</h3>
					<p className="text-small text-text-muted">
						{leitura ?? "Carregando o ranking…"}
					</p>
				</div>
				<div className="flex items-center gap-2">
					{efeito !== "variacao" && (
						<Button
							variant="ghost"
							size="xs"
							onClick={() => onEfeito("variacao")}
						>
							<XIcon aria-hidden />
							Variação total
						</Button>
					)}
					<div className="flex rounded-md border border-border p-0.5">
						{MEDIDAS.map((m) => (
							<button
								key={m.id}
								type="button"
								aria-pressed={medida === m.id}
								aria-label={m.nome}
								onClick={() => setMedida(m.id)}
								className={cn(
									"h-6 min-w-7 cursor-pointer rounded-sm px-1.5 text-small tabular-nums outline-none transition-colors focus-visible:ring-3 focus-visible:ring-focus-ring/50",
									medida === m.id
										? "bg-pressed font-medium text-text"
										: "text-text-muted hover:bg-hover hover:text-text",
								)}
							>
								{m.rotulo}
							</button>
						))}
					</div>
				</div>
			</div>
			<ol className="flex flex-col">
				{ranking
					? ranking.itens.map(({ linha, valor, pct, fracao }, i) => {
							const proximo = navegavel ? filtroAoAbrir(recorte, linha) : null;
							return (
								<li
									key={linha.segmento}
									className="group relative grid h-9 grid-cols-[1.5rem_minmax(0,12rem)_minmax(3rem,1fr)_auto] items-center gap-3 rounded-sm px-1 transition-colors hover:bg-hover"
									onPointerEnter={() => navegavel && onDestaque?.(linha)}
									onPointerLeave={() => navegavel && onDestaque?.(null)}
								>
									<span className="text-small text-text-muted tabular-nums">
										{i + 1}º
									</span>
									{proximo ? (
										<button
											type="button"
											onClick={() => onAbrir(proximo)}
											onFocus={() => onDestaque?.(linha)}
											onBlur={() => onDestaque?.(null)}
											aria-label={`Abrir ${linha.segmento}`}
											className="min-w-0 cursor-pointer truncate text-left text-body text-text outline-none after:absolute after:inset-0 after:rounded-sm after:content-[''] focus-visible:after:shadow-[inset_0_0_0_2px_var(--color-focus-ring)]"
										>
											{linha.segmento}
										</button>
									) : (
										<span className="min-w-0 truncate text-body text-text">
											{linha.segmento}
										</span>
									)}
									<span aria-hidden className="relative h-2.5">
										<span
											className={cn(
												"absolute inset-y-0 left-0 min-w-0.5 rounded-sm transition-[width] duration-300 motion-reduce:transition-none",
												// Sem queda, a lista são as menores altas: barra neutra, para não
												// chamar o olho para quem subiu mais.
												!ranking.houveQueda
													? "bg-border-strong"
													: valor < 0
														? "bg-danger"
														: "bg-success",
											)}
											style={{ width: `${fracao * 100}%` }}
										/>
									</span>
									<span
										className={cn(
											"flex items-baseline justify-end gap-2 text-right tabular-nums",
											valor < 0
												? "text-danger"
												: valor > 0
													? "text-success"
													: "text-text-muted",
										)}
									>
										{medida === "pct" && pct !== null ? (
											<>
												<span className="hidden text-small text-text-muted @md:inline">
													{formatBRL(valor, { sinal: true })}
												</span>
												<span className="min-w-14 text-body">
													{formatPct(pct, { sinal: true })}
												</span>
											</>
										) : (
											<>
												{pct !== null && (
													<span className="hidden text-small text-text-muted @md:inline">
														{formatPct(pct, { sinal: true })}
													</span>
												)}
												<span className="text-body">
													{formatBRL(valor, { sinal: true })}
												</span>
											</>
										)}
									</span>
								</li>
							);
						})
					: Array.from({ length: LIMITE }, (_, i) => (
							<li
								// biome-ignore lint/suspicious/noArrayIndexKey: molde fixo, sem identidade.
								key={i}
								aria-hidden
								className="grid h-9 grid-cols-[1.5rem_minmax(0,12rem)_minmax(3rem,1fr)_auto] items-center gap-3 px-1"
							>
								<span className="h-2 w-3 rounded-sm bg-pressed" />
								<span className="h-2 w-24 rounded-sm bg-pressed" />
								<span
									className="h-2.5 rounded-sm bg-pressed"
									style={{ width: `${90 - i * 15}%` }}
								/>
								<span className="h-2 w-20 rounded-sm bg-pressed" />
							</li>
						))}
			</ol>
		</section>
	);
}
