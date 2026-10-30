import {
	ArrowsClockwiseIcon,
	CaretDownIcon,
	CaretRightIcon,
	CheckIcon,
	CodeIcon,
	CopyIcon,
	InfoIcon,
	SpinnerGapIcon,
	TableIcon,
	WarningIcon,
	XCircleIcon,
} from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { formatDataHora, formatNumero, formatSegundos } from "#/lib/format";
import { cn } from "#/lib/utils";
import {
	formatarCelulaResultado,
	nomeAmigavelView,
	rotuloConfianca,
	rotuloStatusResposta,
} from "../conversions";
import type { TurnoConversa } from "../types";

const PONTO_STATUS = {
	success: "bg-success",
	info: "bg-info",
	warning: "bg-warning",
	danger: "bg-danger",
} as const;

const PONTO_CONFIANCA = {
	success: "bg-success",
	warning: "bg-warning",
	neutral: "bg-text-muted",
} as const;

export function AgenteTurnoItem({
	turno,
	onRetry,
	compacto = false,
	mostrarHorario = false,
}: {
	turno: TurnoConversa;
	onRetry: (id: string) => void;
	compacto?: boolean;
	mostrarHorario?: boolean;
}) {
	const [detalhesAbertos, setDetalhesAbertos] = useState(false);
	const [tabelaAberta, setTabelaAberta] = useState<boolean | null>(null);
	const [sqlAberto, setSqlAberto] = useState(false);
	const [copiado, setCopiado] = useState(false);
	const [respostaCopiada, setRespostaCopiada] = useState(false);
	const timerCopia = useRef<number | undefined>(undefined);
	const timerCopiaResposta = useRef<number | undefined>(undefined);

	useEffect(
		() => () => {
			window.clearTimeout(timerCopia.current);
			window.clearTimeout(timerCopiaResposta.current);
		},
		[],
	);

	const resposta = turno.resposta;
	const status = resposta ? rotuloStatusResposta(resposta.status) : null;
	const confianca = resposta ? rotuloConfianca(resposta.confidence) : null;
	const tabelaPadrao =
		!compacto &&
		!!resposta &&
		resposta.rows.length > 0 &&
		resposta.rows.length <= 6;
	const tabelaVisivel = tabelaAberta ?? tabelaPadrao;
	const colunas =
		resposta && resposta.rows.length > 0
			? Object.keys(resposta.rows[0] ?? {})
			: [];

	async function copiarSql() {
		if (!resposta?.sql || !navigator.clipboard) return;
		try {
			await navigator.clipboard.writeText(resposta.sql);
			setCopiado(true);
			window.clearTimeout(timerCopia.current);
			timerCopia.current = window.setTimeout(() => setCopiado(false), 1800);
		} catch {
			setCopiado(false);
		}
	}

	async function copiarResposta() {
		if (!resposta?.answer || !navigator.clipboard) return;
		try {
			await navigator.clipboard.writeText(resposta.answer);
			setRespostaCopiada(true);
			window.clearTimeout(timerCopiaResposta.current);
			timerCopiaResposta.current = window.setTimeout(
				() => setRespostaCopiada(false),
				1800,
			);
		} catch {
			setRespostaCopiada(false);
		}
	}

	return (
		<article className="space-y-4">
			{mostrarHorario && (
				<div className="text-center text-small text-text-muted">
					{formatDataHora(turno.criadoEm)}
				</div>
			)}

			<p className="ml-auto w-fit max-w-[85%] rounded-lg border border-border bg-surface-2 px-3.5 py-2 text-body text-text">
				{turno.question}
			</p>

			<div className="min-w-0 space-y-3">
				{turno.status === "pending" && (
					<p className="inline-flex items-center gap-2 text-small text-text-muted motion-safe:animate-pulse">
						<SpinnerGapIcon
							aria-hidden
							className="size-3.5 shrink-0 motion-safe:animate-spin"
						/>
						Pensando…
					</p>
				)}

				{turno.status === "error" && (
					<div className="flex flex-wrap items-center gap-3 rounded-md border border-danger bg-danger-subtle p-3 text-body text-danger">
						<XCircleIcon aria-hidden className="size-4 shrink-0" />
						<p className="min-w-0 flex-1">{turno.erro}</p>
						<Button
							type="button"
							variant="outline"
							size="xs"
							onClick={() => onRetry(turno.id)}
						>
							<ArrowsClockwiseIcon aria-hidden />
							Tentar novamente
						</Button>
					</div>
				)}

				{turno.status === "completed" && resposta && status && confianca && (
					<>
						<div className="space-y-1.5">
							<button
								type="button"
								onClick={() => setDetalhesAbertos(!detalhesAbertos)}
								aria-expanded={detalhesAbertos}
								className="inline-flex cursor-pointer items-center gap-1 rounded-sm text-small text-text-muted transition-colors hover:text-text"
							>
								<span>Trabalhou por {formatSegundos(resposta.latency_ms)}</span>
								{detalhesAbertos ? (
									<CaretDownIcon aria-hidden className="size-3" />
								) : (
									<CaretRightIcon aria-hidden className="size-3" />
								)}
							</button>

							{detalhesAbertos && (
								<div className="flex flex-wrap items-center gap-1.5 pt-0.5">
									<Badge variant="outline">
										<span
											aria-hidden
											className={cn(
												"size-1.5 rounded-full",
												PONTO_STATUS[status.tom],
											)}
										/>
										<span>{status.rotulo}</span>
									</Badge>
									{resposta.status === "answered" && (
										<Badge variant="outline">
											<span
												aria-hidden
												className={cn(
													"size-1.5 rounded-full",
													PONTO_CONFIANCA[confianca.tom],
												)}
											/>
											<span>{confianca.rotulo}</span>
										</Badge>
									)}
									{resposta.sources.map((fonte) => (
										<Badge key={fonte} variant="secondary">
											{nomeAmigavelView(fonte)}
										</Badge>
									))}
									<span className="font-mono text-small text-text-muted">
										#{resposta.audit_id}
									</span>
								</div>
							)}
						</div>

						<p className="whitespace-pre-line text-body text-text">
							{resposta.answer}
						</p>

						{resposta.status === "clarify" &&
							resposta.clarification &&
							resposta.clarification !== resposta.answer && (
								<p className="rounded-md border border-info bg-info-subtle p-2.5 text-body text-text">
									{resposta.clarification}
								</p>
							)}

						{resposta.status !== "answered" &&
							resposta.refused_reason &&
							resposta.refused_reason !== resposta.answer && (
								<p className="rounded-md border border-warning bg-warning-subtle p-2.5 text-small text-text">
									{resposta.refused_reason}
								</p>
							)}

						{resposta.assumptions.length > 0 && (
							<div className="flex gap-2 rounded-md border border-border bg-surface-2/50 p-2.5 text-small text-text-muted">
								<InfoIcon aria-hidden className="mt-0.5 size-3.5 shrink-0" />
								<ul className="min-w-0 list-disc space-y-0.5 pl-3.5">
									{resposta.assumptions.map((suposicao) => (
										<li key={suposicao}>{suposicao}</li>
									))}
								</ul>
							</div>
						)}

						{resposta.truncated && (
							<p className="flex items-center gap-1.5 text-small text-warning">
								<WarningIcon aria-hidden className="size-3.5 shrink-0" />
								Mostrando amostra de {resposta.rows.length} linhas de{" "}
								{formatNumero(resposta.row_count)} registros.
							</p>
						)}

						{tabelaVisivel && resposta.rows.length > 0 && (
							<div className="overflow-x-auto rounded-md border border-border bg-surface-2/40">
								<table className="w-full border-collapse text-small">
									<thead>
										<tr className="border-b border-border">
											{colunas.map((coluna) => (
												<th
													key={coluna}
													scope="col"
													className="whitespace-nowrap px-3 py-2 text-left font-medium text-text-muted"
												>
													{coluna}
												</th>
											))}
										</tr>
									</thead>
									<tbody>
										{resposta.rows.map((linha, indice) => (
											<tr
												// biome-ignore lint/suspicious/noArrayIndexKey: linhas do resultado não têm identificador próprio
												key={indice}
												className="border-b border-border last:border-b-0"
											>
												{colunas.map((coluna) => (
													<td
														key={coluna}
														className="whitespace-nowrap px-3 py-2 tabular-nums text-text"
													>
														{formatarCelulaResultado(coluna, linha[coluna])}
													</td>
												))}
											</tr>
										))}
									</tbody>
								</table>
							</div>
						)}

						{sqlAberto && resposta.sql && (
							<div className="relative">
								<pre className="overflow-x-auto rounded-md border border-border bg-bg p-3 pr-10 font-mono text-code text-text">
									{resposta.sql}
								</pre>
								<Button
									type="button"
									variant="ghost"
									size="icon-xs"
									className="absolute top-1.5 right-1.5"
									aria-label={copiado ? "SQL copiado" : "Copiar SQL"}
									onClick={copiarSql}
								>
									{copiado ? (
										<CheckIcon aria-hidden className="size-3.5 text-success" />
									) : (
										<CopyIcon aria-hidden className="size-3.5" />
									)}
								</Button>
							</div>
						)}

						<div className="flex flex-wrap items-center gap-1 pt-0.5 text-text-muted">
							<Button
								type="button"
								variant="ghost"
								size="icon-xs"
								className="text-text-muted hover:text-text"
								aria-label={
									respostaCopiada ? "Resposta copiada" : "Copiar resposta"
								}
								title={respostaCopiada ? "Resposta copiada" : "Copiar resposta"}
								onClick={copiarResposta}
							>
								{respostaCopiada ? (
									<CheckIcon aria-hidden className="size-3.5 text-success" />
								) : (
									<CopyIcon aria-hidden className="size-3.5" />
								)}
							</Button>
							{resposta.rows.length > 0 && (
								<Button
									type="button"
									variant="ghost"
									size="xs"
									className="text-text-muted hover:text-text"
									aria-expanded={tabelaVisivel}
									onClick={() => setTabelaAberta(!tabelaVisivel)}
								>
									<TableIcon aria-hidden />
									Tabela ({resposta.rows.length})
								</Button>
							)}
							{resposta.sql && (
								<Button
									type="button"
									variant="ghost"
									size="xs"
									className="text-text-muted hover:text-text"
									aria-expanded={sqlAberto}
									onClick={() => setSqlAberto(!sqlAberto)}
								>
									<CodeIcon aria-hidden />
									SQL
								</Button>
							)}
						</div>
					</>
				)}
			</div>
		</article>
	);
}
