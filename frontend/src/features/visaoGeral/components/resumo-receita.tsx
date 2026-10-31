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
import { useFiltrosPortal } from "#/features/filtros";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import {
	formatBRL,
	formatKWh,
	formatPct,
	formatPeriodoCurto,
} from "#/lib/format";
import { cn } from "#/lib/utils";
import { leitura, MESES_MAX_JANELA, mesesDoPeriodo } from "../conversions";
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
 * A pergunta da diretoria na tela: a receita e a energia faturadas do período atual contra a
 * base escolhida na barra comum, e a tesoura entre as duas ao longo da série. O porquê fica na
 * ponte de receita, aberta no mesmo par.
 */
export function ResumoReceita({
	par,
	recorte,
	semPeriodo,
}: {
	par: ParPeriodos | undefined;
	recorte: Recorte;
	/** A Gold não tem dois meses para comparar: o período ainda não foi escolhido. */
	semPeriodo: boolean;
}) {
	const { searchPara } = useFiltrosPortal();
	const comparacao = useComparacaoIndicadores(par, recorte);
	const serie = useTesoura(par, recorte);
	const meses = par ? mesesDoPeriodo(par.periodo_atual) : undefined;
	const janela = meses === 1 ? "mês" : "meses";
	const corridos = meses === 1 ? "mês corrido" : "meses corridos";
	const acimaDoLimite = meses !== undefined && meses > MESES_MAX_JANELA;
	const dados = comparacao.data;
	const frase = leitura(
		dados?.variacao_pct.receita_faturada,
		dados?.variacao_pct.kwh_faturado,
	);

	let numeros: ReactNode;
	if (comparacao.isError) {
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
					onClick={() => void comparacao.refetch()}
				>
					<ArrowsClockwiseIcon aria-hidden />
					Tentar de novo
				</Button>
			</div>
		);
	} else if (semPeriodo) {
		numeros = (
			<p className="text-pretty text-body text-text-muted">
				Escolha um período na barra de filtros para comparar a receita e a
				energia.
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

	const somas = serie.data?.somas;
	return (
		<section
			aria-labelledby="resumo-titulo"
			aria-busy={comparacao.isFetching || serie.isFetching || undefined}
			className="@container flex flex-col gap-5 rounded-md border border-border bg-surface-1 p-5 shadow-edge"
		>
			<header className="flex flex-col gap-1.5">
				<h2 id="resumo-titulo" className="text-balance font-display text-title">
					{frase ?? "Receita e energia faturadas"}
				</h2>
				{par ? (
					<p className="text-pretty text-body text-text-muted">
						{formatPeriodoCurto(par.periodo_atual)} vs{" "}
						{formatPeriodoCurto(par.periodo_base)}.
					</p>
				) : null}
			</header>
			<div className="grid gap-6 lg:grid-cols-[minmax(13rem,16rem)_minmax(0,1fr)]">
				<div className="flex flex-col gap-4">
					{numeros}
					{par ? (
						<Link
							to="/receita"
							search={searchPara("/receita") as never}
							className={buttonVariants({
								variant: "outline",
								size: "sm",
								className: "self-start",
							})}
						>
							Abrir a ponte de receita
							<CaretRightIcon aria-hidden />
						</Link>
					) : null}
				</div>
				{par && meses !== undefined ? (
					acimaDoLimite ? (
						<p className="text-pretty text-body text-text-muted lg:border-border lg:border-l lg:pl-6">
							A tesoura vai até {MESES_MAX_JANELA} meses. Os totais do período
							continuam disponíveis.
						</p>
					) : (
						<TrendChart
							label={`Receita e energia faturadas em ${meses} ${corridos}, variação sobre a primeira janela`}
							categories={serie.data?.categories}
							series={serie.data?.series}
							formatValue={variacao}
							categoryLabel={`Janela de ${meses} ${janela}`}
							summary={`Soma de ${meses} ${corridos}, em variação sobre a primeira janela da série.`}
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
							loading={serie.isFetching}
							error={
								serie.isError ? "Não foi possível carregar a série." : null
							}
							onRetry={() => serie.refetch()}
							emptyMessage={`A tesoura precisa de pelo menos duas janelas completas de ${meses} ${janela} no intervalo selecionado.`}
							height={240}
							className="rounded-none border-0 bg-transparent p-0 shadow-none lg:border-border lg:border-l lg:pl-6"
						/>
					)
				) : null}
			</div>
		</section>
	);
}
