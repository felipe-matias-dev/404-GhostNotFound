import { TrendChart } from "#/components/ui/trend-chart";
import {
	formatBRL,
	formatCompetencia,
	formatKWh,
	formatNumero,
	formatPct,
} from "#/lib/format";
import { toConsumoChart } from "../conversions";
import type { Uc360 } from "../types";

const bandeiras = {
	verde: "Verde",
	amarela: "Amarela",
	vermelha_p1: "Vermelha patamar 1",
	vermelha_p2: "Vermelha patamar 2",
};
const tendencias = {
	subiu: "O consumo subiu",
	caiu: "O consumo caiu",
	estavel: "Consumo na faixa de estabilidade (−10% a +10%)",
	sem_comparacao: "Sem base para comparar o consumo",
};

export function ConsumoUc({ data }: { data: Uc360 }) {
	const consumo = data.consumo;
	const atual = consumo.meses.at(-1);
	const chart = toConsumoChart(consumo.meses);
	return (
		<section
			aria-labelledby="uc-consumo"
			className="flex min-w-0 flex-col gap-4"
		>
			<div>
				<h2 id="uc-consumo" className="text-heading">
					Consumo faturado
				</h2>
				<p className="mt-2 text-title text-balance">
					{tendencias[consumo.tendencia]}
				</p>
				<p className="mt-1 text-small text-text-muted">
					{consumo.referencia
						? `${formatCompetencia(consumo.referencia)} em comparação com o mesmo mês do ano anterior. Referência da Gold inteira, não da última fatura desta UC.`
						: "A Gold não tem competência de faturamento disponível."}
				</p>
			</div>
			<dl className="grid grid-cols-2 gap-4 rounded-md border border-border bg-surface-1 p-4 sm:grid-cols-4">
				<div>
					<dt className="text-small text-text-muted">Mês de referência</dt>
					<dd className="mt-1 font-mono text-body tabular-nums">
						{atual?.kwh_faturado == null
							? "Não informado"
							: formatKWh(atual.kwh_faturado)}
					</dd>
				</div>
				<div>
					<dt className="text-small text-text-muted">Mesmo mês anterior</dt>
					<dd className="mt-1 font-mono text-body tabular-nums">
						{atual?.kwh_ano_anterior == null
							? "Não informado"
							: formatKWh(atual.kwh_ano_anterior)}
					</dd>
				</div>
				<div>
					<dt className="text-small text-text-muted">Variação do mês</dt>
					<dd className="mt-1 font-mono text-body tabular-nums">
						{consumo.variacao_ultimo_mes_pct == null
							? "Não disponível"
							: formatPct(consumo.variacao_ultimo_mes_pct / 100, {
									sinal: true,
								})}
					</dd>
				</div>
				<div>
					<dt className="text-small text-text-muted">Variação em 12 meses</dt>
					<dd className="mt-1 font-mono text-body tabular-nums">
						{consumo.variacao_12m_pct == null
							? "Não disponível"
							: formatPct(consumo.variacao_12m_pct / 100, { sinal: true })}
					</dd>
				</div>
			</dl>
			<p className="text-small text-text-muted">
				Meses com fatura nos dois anos: {formatNumero(consumo.meses_comparados)}
				. A variação de 12 meses usa só esses pares. Lacunas não representam
				consumo zero.
			</p>
			{consumo.tendencia === "sem_comparacao" && (
				<p className="text-small text-text-muted">
					{atual?.kwh_ano_anterior === 0
						? "Comparação do mês indisponível: base zero."
						: "A comparação do mês exige fatura nos dois anos e base diferente de zero."}
				</p>
			)}
			<div className="border-border border-b pb-4">
				<p className="text-small text-text-muted">
					Conta do mês de referência · {formatCompetencia(consumo.referencia)}
				</p>
				<p className="mt-1 font-mono text-heading tabular-nums">
					{atual?.receita_faturada == null
						? "Não informado"
						: formatBRL(atual.receita_faturada)}
				</p>
				<dl className="mt-3 grid grid-cols-2 gap-3 text-small">
					<div>
						<dt className="text-text-muted">Dias faturados</dt>
						<dd className="mt-1 font-mono tabular-nums">
							{atual?.dias_faturados == null
								? "Não informado"
								: formatNumero(atual.dias_faturados)}
						</dd>
					</div>
					<div>
						<dt className="text-text-muted">Bandeira</dt>
						<dd className="mt-1">
							{atual?.bandeira ? bandeiras[atual.bandeira] : "Não informado"}
						</dd>
					</div>
				</dl>
			</div>
			<p className="text-small text-text-muted">
				A comparação de consumo não explica sozinha a variação do valor da
				conta.
			</p>
			<TrendChart
				label="Consumo faturado comparado ao ano anterior"
				categories={chart.categories}
				series={chart.series}
				height={240}
				zeroBaseline
				formatValue={formatKWh}
				categoryLabel="Competências comparadas"
				emptyMessage="Sem histórico de consumo faturado."
			/>
		</section>
	);
}
