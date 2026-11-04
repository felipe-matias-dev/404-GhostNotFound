import type { ReactElement } from "react";
import { KpiCard } from "#/components/ui/kpi-card";
import type { Recorte } from "#/lib/filtros";
import { formatKWh, formatNumero, formatPct } from "#/lib/format";
import { useIndicadoresPerdas } from "../hooks/use-indicadores-perdas";

const NOTA = "text-small text-text-muted";

const contagem = (total: number, singular: string, plural: string) =>
	`${formatNumero(total)} ${total === 1 ? singular : plural}`;

/**
 * Alto da tela de Perdas: o que está na fila, as ordens em andamento e o quanto as inspeções
 * do portal acertaram. Todos os números vêm prontos do backend; a taxa histórica da Gold é só referência.
 */
export function IndicadoresPerdas({
	recorte,
}: {
	recorte: Recorte;
}): ReactElement {
	const { data, isPending, isError, refetch } = useIndicadoresPerdas(recorte);
	const comum = {
		loading: isPending,
		error: isError ? "Não foi possível carregar os indicadores." : null,
		onRetry: () => void refetch(),
		className: "rounded-none border-0 px-5 py-4 shadow-none",
	};
	const portal = data?.portal;
	const gold = data?.gold;

	return (
		<section
			aria-labelledby="perdas-indicadores-titulo"
			className="@container flex min-w-0 flex-col overflow-hidden rounded-md border border-border bg-surface-1 shadow-edge"
		>
			<h2 id="perdas-indicadores-titulo" className="sr-only">
				Indicadores de perdas
			</h2>
			<div className="grid grid-cols-2 gap-px bg-border @4xl:grid-cols-3 @6xl:grid-cols-6">
				<KpiCard
					{...comum}
					label="Suspeitas sem ordem"
					value={data?.suspeitas_sem_ordem_ativa}
					format={formatNumero}
					hint="UCs da fila de suspeitas que ainda não têm ordem de inspeção gerada ou em campo."
				>
					{data && (
						<p className={NOTA}>de {formatNumero(data.suspeitas)} suspeitas</p>
					)}
				</KpiCard>
				<KpiCard
					{...comum}
					label="Energia a recuperar"
					value={data ? data.kwh_recuperavel_est_sem_ordem : undefined}
					format={formatKWh}
					emptyMessage="Sem estimativa nas suspeitas."
					hint="Estimativa de kWh por mês que as suspeitas sem ordem ativa devem devolver à receita se a irregularidade se confirmar."
				>
					{data && <p className={NOTA}>por mês, suspeitas sem ordem</p>}
				</KpiCard>
				<KpiCard
					{...comum}
					label="Ordens geradas"
					value={data?.ordens_geradas}
					format={formatNumero}
					hint="Ordens de inspeção criadas que ainda não foram enviadas a campo."
				/>
				<KpiCard
					{...comum}
					label="Ordens em campo"
					value={data?.ordens_em_campo}
					format={formatNumero}
					hint="Ordens enviadas a campo que aguardam o resultado da equipe."
				/>
				<KpiCard
					{...comum}
					label="Irregularidade nas inspeções"
					value={portal ? portal.taxa_irregularidade : undefined}
					format={formatPct}
					emptyMessage="Sem vistorias concluídas."
					hint="Das vistorias concluídas no portal (irregulares e regulares), a parcela que confirmou irregularidade. Ordens não realizadas não entram. A taxa da Gold é o histórico de referência."
				>
					{portal && gold && (
						<div className="flex flex-col gap-0.5">
							<p className={NOTA}>
								{contagem(portal.irregulares, "irregular", "irregulares")},{" "}
								{contagem(portal.regulares, "regular", "regulares")}
								{portal.nao_realizadas > 0
									? `, ${contagem(portal.nao_realizadas, "não realizada", "não realizadas")}`
									: ""}
							</p>
							<p className={NOTA}>
								{gold.taxa_irregularidade == null
									? "Sem histórico na Gold"
									: `Histórico (Gold): ${formatPct(gold.taxa_irregularidade)} em ${contagem(gold.inspecoes, "inspeção", "inspeções")}`}
							</p>
						</div>
					)}
				</KpiCard>
				<KpiCard
					{...comum}
					label="Energia recuperada"
					value={portal?.kwh_recuperado}
					format={formatKWh}
					hint="kWh recuperados nas irregularidades confirmadas pelas ordens concluídas no portal."
				>
					{portal && <p className={NOTA}>inspeções do portal</p>}
				</KpiCard>
			</div>
		</section>
	);
}
