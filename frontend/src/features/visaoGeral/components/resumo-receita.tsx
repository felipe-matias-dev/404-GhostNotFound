import {
	ArrowsClockwiseIcon,
	CaretRightIcon,
	WarningCircleIcon,
} from "@phosphor-icons/react";
import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Button, buttonVariants } from "#/components/ui/button";
import { KpiDelta, KpiValue } from "#/components/ui/kpi-card";
import { TrendChart } from "#/components/ui/trend-chart";
import {
	formatBRL,
	formatKWh,
	formatNumero,
	formatPeriodoCurto,
} from "#/lib/format";
import { cn } from "#/lib/utils";
import { type Janelas, leitura } from "../conversions";
import { useComparacaoReceita, useTesoura } from "../hooks/use-indicadores";

const receita = (valor: number) => formatBRL(valor, { compacto: true });
const energia = (valor: number) => formatKWh(valor, { compacto: true });

function Numero({
	label,
	value,
	format,
	pct,
	className,
}: {
	label: string;
	value: number;
	format: (valor: number) => string;
	/** Variação em %, como vem da API. */
	pct: number | null;
	className?: string;
}) {
	return (
		<div className="flex flex-col gap-1.5">
			<dt className="text-small text-text-muted">{label}</dt>
			<dd className="flex flex-col items-start gap-1.5">
				<KpiValue value={value} format={format} className={className} />
				{pct === null ? null : <KpiDelta value={pct / 100} />}
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
	/** A série carregou, mas não tem 24 meses seguidos: não há duas janelas de 12. */
	semJanelas: boolean;
	erroSerie: boolean;
	onRetrySerie: () => void;
}) {
	const comparacao = useComparacaoReceita(janelas);
	const tesoura = useTesoura();
	const dados = comparacao.data;
	const frase = leitura(dados?.variacao_receita_pct, dados?.variacao_kwh_pct);

	let numeros: ReactNode;
	if (erroSerie || comparacao.isError) {
		numeros = (
			<div className="flex flex-col items-start gap-2">
				<p className="flex items-center gap-1.5 text-body">
					<WarningCircleIcon
						aria-hidden
						className="size-4 shrink-0 text-danger"
					/>
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
				A comparação de 12 meses precisa de 24 meses seguidos na Gold.
			</p>
		);
	} else if (!dados) {
		numeros = <Molde />;
	} else {
		numeros = (
			<dl className="flex flex-col gap-5">
				<Numero
					label="Receita faturada"
					value={dados.atual.receita_faturada}
					format={receita}
					pct={dados.variacao_receita_pct}
					className="@3xs:text-display"
				/>
				<Numero
					label="Energia faturada"
					value={dados.atual.kwh_faturado}
					format={energia}
					pct={dados.variacao_kwh_pct}
				/>
			</dl>
		);
	}

	const somas = tesoura.data?.somas;
	return (
		<section
			aria-labelledby="resumo-titulo"
			aria-busy={comparacao.isFetching || undefined}
			className="flex flex-col gap-5 rounded-md border border-border bg-surface-1 p-5 shadow-edge"
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
			<div className="grid gap-5 lg:grid-cols-[minmax(14rem,18rem)_minmax(0,1fr)]">
				<div className="@container flex flex-col justify-between gap-5">
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
					label="Receita e energia faturadas em 12 meses corridos, índice sobre a primeira janela"
					categories={tesoura.data?.categories}
					series={tesoura.data?.series}
					formatValue={formatNumero}
					categoryLabel="Janela de 12 meses"
					summary="Soma de 12 meses corridos; a primeira janela vale 100."
					tooltipFooter={(indice) => {
						const soma = somas?.[indice];
						return soma ? (
							<p className="text-text-muted tabular-nums">
								{receita(soma.receita)} · {energia(soma.kwh)}
							</p>
						) : null;
					}}
					loading={tesoura.isFetching}
					error={erroSerie ? "Não foi possível carregar a série." : null}
					onRetry={onRetrySerie}
					emptyMessage="A tesoura precisa de 13 meses seguidos na Gold."
					height={260}
					className="rounded-none border-0 bg-transparent p-0 shadow-none lg:border-border lg:border-l lg:pl-5"
				/>
			</div>
		</section>
	);
}
