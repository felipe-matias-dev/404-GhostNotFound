import {
	ArrowsClockwiseIcon,
	CaretRightIcon,
	XCircleIcon,
} from "@phosphor-icons/react";
import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Button, buttonVariants } from "#/components/ui/button";
import { KpiDelta, KpiValue } from "#/components/ui/kpi-card";
import { TrendChart } from "#/components/ui/trend-chart";
import {
	formatBRL,
	formatKWh,
	formatPct,
	formatPeriodoCurto,
} from "#/lib/format";
import { cn } from "#/lib/utils";
import { type Janelas, leitura } from "../conversions";
import { useComparacaoIndicadores, useTesoura } from "../hooks/use-indicadores";
import { DEFINICOES, type DefinicaoIndicador } from "../indicadores";

const receita = (valor: number) => formatBRL(valor, { compacto: true });
const energia = (valor: number) => formatKWh(valor, { compacto: true });
const variacao = (valor: number) => formatPct(valor, { sinal: true });
// As duas séries da tesoura: a faixa entre elas é a distância entre receita e energia.
const TESOURA = ["receita", "kwh"] as const;

function Numero({
	label,
	value,
	format,
	pct,
	favorable,
}: {
	label: string;
	value: number;
	format: (valor: number) => string;
	/** Variação em %, como vem da API. */
	pct: number | null;
	favorable: DefinicaoIndicador["favorable"];
}) {
	return (
		<div className="flex flex-col gap-1.5">
			<dt className="text-small text-text-muted">{label}</dt>
			<dd className="flex flex-col items-start gap-1.5">
				<KpiValue value={value} format={format} />
				{pct === null ? null : (
					<KpiDelta value={pct / 100} favorable={favorable} />
				)}
			</dd>
		</div>
	);
}

function Molde() {
	return (
		<div aria-hidden className="flex flex-col gap-5">
			{["w-3/4", "w-1/2"].map((largura) => (
				<div key={largura} className="flex flex-col gap-2">
					<div className="h-3 w-24 rounded-sm bg-pressed" />
					<div className={cn("h-10 rounded-sm bg-pressed", largura)} />
				</div>
			))}
		</div>
	);
}

/**
 * A pergunta da diretoria numa tela: a receita e a energia faturadas dos 12 meses mais
 * recentes contra os 12 primeiros da base, e a tesoura entre as duas ao longo da série. O
 * porquê fica na ponte de receita, aberta no mesmo par de janelas.
 */
export function ResumoReceita({
	janelas,
	semJanelas,
	erroSerie,
	onRetrySerie,
}: {
	janelas: Janelas | undefined;
	/** Não há duas janelas completas de 12 meses sem sobreposição. */
	semJanelas: boolean;
	erroSerie: boolean;
	onRetrySerie: () => void;
}) {
	const comparacao = useComparacaoIndicadores(
		janelas
			? { periodo_base: janelas.base, periodo_atual: janelas.atual }
			: undefined,
	);
	const tesoura = useTesoura();
	const dados = comparacao.data;
	const frase = leitura(
		dados?.variacao_pct.receita_faturada,
		dados?.variacao_pct.kwh_faturado,
	);

	let numeros: ReactNode;
	if (erroSerie || comparacao.isError) {
		numeros = (
			<div className="flex flex-col items-start gap-2">
				<p className="flex items-center gap-1.5 text-body">
					<XCircleIcon aria-hidden className="size-4 shrink-0 text-danger" />
					Não foi possível carregar a receita e a energia.
				</p>
				<Button
					variant="ghost"
					size="xs"
					className="-ml-1.5"
					onClick={() =>
						erroSerie ? onRetrySerie() : void comparacao.refetch()
					}
				>
					<ArrowsClockwiseIcon aria-hidden />
					Tentar de novo
				</Button>
			</div>
		);
	} else if (semJanelas) {
		numeros = (
			<p className="text-body text-text-muted text-pretty">
				A comparação precisa de duas janelas completas de 12 meses sem
				sobreposição.
			</p>
		);
	} else if (!dados) {
		numeros = <Molde />;
	} else {
		numeros = (
			<dl className="flex flex-col gap-4">
				<Numero
					label="Receita faturada"
					value={dados.atual.receita_faturada}
					format={receita}
					pct={dados.variacao_pct.receita_faturada}
					favorable={DEFINICOES.receita_faturada.favorable}
				/>
				<Numero
					label="Energia faturada"
					value={dados.atual.kwh_faturado}
					format={energia}
					pct={dados.variacao_pct.kwh_faturado}
					favorable={DEFINICOES.kwh_faturado.favorable}
				/>
			</dl>
		);
	}

	const somas = tesoura.data?.somas;
	return (
		<section
			aria-labelledby="resumo-titulo"
			aria-busy={comparacao.isFetching || undefined}
			className="@container flex flex-col gap-5 rounded-md border border-border bg-surface-1 p-5 shadow-edge"
		>
			<header className="flex flex-col gap-1.5">
				<h2 id="resumo-titulo" className="text-balance font-display text-title">
					{frase ?? "Receita e energia faturadas"}
				</h2>
				{janelas ? (
					<p className="text-pretty text-body text-text-muted">
						Últimos 12 meses ({formatPeriodoCurto(janelas.atual)}) contra os 12
						primeiros da base ({formatPeriodoCurto(janelas.base)}).
					</p>
				) : null}
			</header>
			<div className="grid gap-6 lg:grid-cols-[minmax(13rem,16rem)_minmax(0,1fr)]">
				<div className="flex flex-col gap-4">
					{numeros}
					<Link
						to="/receita"
						search={
							janelas
								? { periodo_base: janelas.base, periodo_atual: janelas.atual }
								: {}
						}
						className={buttonVariants({
							variant: "outline",
							size: "sm",
							className: "self-start",
						})}
					>
						Abrir a ponte de receita
						<CaretRightIcon aria-hidden />
					</Link>
				</div>
				<TrendChart
					label="Receita e energia faturadas em 12 meses corridos, variação sobre a primeira janela"
					categories={tesoura.data?.categories}
					series={tesoura.data?.series}
					formatValue={variacao}
					categoryLabel="Janela de 12 meses"
					summary="Soma de 12 meses corridos, em variação sobre a primeira janela da série."
					reference={0}
					endLabels
					band={TESOURA}
					tooltipFooter={(indice) => {
						const soma = somas?.[indice];
						return soma ? (
							<p className="text-text-muted tabular-nums">
								{receita(soma.receita)} · {energia(soma.kwh)}
							</p>
						) : null;
					}}
					loading={tesoura.isFetching}
					error={tesoura.isError ? "Não foi possível carregar a série." : null}
					onRetry={() => tesoura.refetch()}
					emptyMessage="A tesoura precisa de pelo menos duas janelas completas de 12 meses."
					height={240}
					className="rounded-none border-0 bg-transparent p-0 shadow-none lg:border-border lg:border-l lg:pl-6"
				/>
			</div>
		</section>
	);
}
