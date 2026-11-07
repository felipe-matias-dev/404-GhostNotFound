import { useComparacaoIndicadores } from "#/features/indicadores";
import type { components } from "#/lib/api-schema.gen";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { formatBRL, formatPeriodoCurto } from "#/lib/format";

type Periodo = components["schemas"]["IndicadoresPeriodoSchema"];

// Compacto como o card da Visão geral: ligar a linha a ele é o objetivo, e os centavos que a
// ponte acumula na base + efeitos (até R$ 0,65 contra a soma da Gold) não aparecem.
const reais = (valor: number) => formatBRL(valor, { compacto: true });

function Conta({ periodo, rotulo }: { periodo: Periodo; rotulo: string }) {
	return (
		<li className="text-pretty">
			<span className="text-text-muted">{rotulo}: </span>
			<span className="font-medium text-text tabular-nums">
				{reais(periodo.receita_faturada)}
			</span>
			<span className="text-text-muted"> = receita de energia </span>
			<span className="text-text tabular-nums">
				{reais(periodo.receita_energia)}
			</span>
			<span className="text-text-muted"> + tributos (governo) </span>
			<span className="text-text tabular-nums">{reais(periodo.tributos)}</span>
		</li>
	);
}

/**
 * A receita faturada do recorte, a mesma da Visão geral, aberta em energia e tributos nos dois
 * períodos da ponte: a ponte explica só a energia, porque o tributo é do governo e viraria
 * "efeito preço" (DEC-073). Os três valores vêm prontos da API; sem eles, a ponte segue sozinha.
 */
export function ReceitaFaturada({
	par,
	recorte,
}: {
	par: ParPeriodos | undefined;
	recorte: Recorte;
}) {
	const { data, isPending, isError } = useComparacaoIndicadores(par, recorte);

	if (isError || (!isPending && !data)) return null;

	return (
		<section
			aria-labelledby="receita-faturada-titulo"
			aria-busy={isPending || undefined}
			className="flex flex-col gap-2 rounded-lg border border-border bg-surface-1 px-4 py-3 text-small"
		>
			<h3
				id="receita-faturada-titulo"
				className="text-body font-medium text-text"
			>
				Receita faturada (com tributos)
			</h3>
			{isPending ? (
				<div aria-hidden className="flex flex-col gap-2">
					<div className="h-4 w-11/12 rounded-sm bg-pressed" />
					<div className="h-4 w-11/12 rounded-sm bg-pressed" />
				</div>
			) : (
				<ul className="flex flex-col gap-1">
					<Conta
						periodo={data.base}
						rotulo={formatPeriodoCurto(par?.periodo_base)}
					/>
					<Conta
						periodo={data.atual}
						rotulo={formatPeriodoCurto(par?.periodo_atual)}
					/>
				</ul>
			)}
			<p className="text-text-muted">
				A ponte abaixo explica só a receita de energia, sem os tributos.
			</p>
		</section>
	);
}
