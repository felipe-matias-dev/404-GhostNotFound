import { formatTempoDecorrido } from "#/lib/format";
import { cn } from "#/lib/utils";
import { STATUS_ORDEM_VISUAL } from "../conversions";
import { useTemposPorEtapa } from "../hooks/use-tempos-por-etapa";
import type { TempoPorEtapa } from "../types";

/**
 * Quanto as OIs levam em cada etapa, somando todas as ordens (o quadro ao lado pode estar
 * filtrado por recorte). Mediana e p90 vêm do backend, sempre com o número de passagens.
 */
export function ResumoTempos() {
	const { data, isPending } = useTemposPorEtapa();

	if (isPending) {
		return (
			<div aria-busy="true" className="grid gap-2 sm:grid-cols-2">
				{[0, 1].map((indice) => (
					<div
						key={indice}
						className="h-12 rounded-lg bg-surface-2 animate-pulse motion-reduce:animate-none"
					/>
				))}
			</div>
		);
	}
	// Sem o resumo, o quadro continua sendo a tela: um erro aqui não precisa de alerta.
	if (!data) return null;

	return (
		<section
			aria-label="Tempo por etapa, todas as ordens"
			className="grid gap-2 sm:grid-cols-2"
		>
			{data.map((linha) => (
				<EtapaDoResumo key={linha.etapa} linha={linha} />
			))}
		</section>
	);
}

function EtapaDoResumo({ linha }: { linha: TempoPorEtapa }) {
	const { rotulo, ponto } = STATUS_ORDEM_VISUAL[linha.etapa];

	return (
		<article className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-lg border border-border bg-surface-1 px-4 py-2 text-small">
			<h3 className="flex items-center gap-2 text-body font-medium">
				<span aria-hidden className={cn("size-2 rounded-full", ponto)} />
				{rotulo}
			</h3>
			{linha.mediana_segundos === null || linha.p90_segundos === null ? (
				<span className="text-text-muted">Sem passagens encerradas</span>
			) : (
				<>
					<span className="tabular-nums">
						Mediana{" "}
						<strong className="font-medium">
							{formatTempoDecorrido(linha.mediana_segundos)}
						</strong>
					</span>
					<span className="tabular-nums">
						9 em 10 levam até{" "}
						<strong className="font-medium">
							{formatTempoDecorrido(linha.p90_segundos)}
						</strong>
					</span>
					<span className="tabular-nums text-text-muted">
						{linha.n} {linha.n === 1 ? "passagem" : "passagens"}
					</span>
				</>
			)}
		</article>
	);
}
