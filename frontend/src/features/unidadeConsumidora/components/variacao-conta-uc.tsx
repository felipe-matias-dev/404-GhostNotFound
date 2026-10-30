import { InfoIcon, WarningCircleIcon } from "@phosphor-icons/react";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "#/components/ui/popover";
import { formatBRL, formatCompetencia } from "#/lib/format";
import { cn } from "#/lib/utils";
import { maiorParte, partesDaConta } from "../conversions";
import type { Uc360 } from "../types";

// Uma grade para todas as linhas: rótulo e valor na largura do maior, e a barra fica com o resto.
// Assim as colunas se alinham e a barra não some na coluna estreita do cadastro.
const GRADE =
	"grid grid-cols-[auto_minmax(3rem,1fr)_auto] items-center gap-x-3 [&>li]:contents [&>li>*]:flex [&>li>*]:h-8 [&>li>*]:items-center";

// Cor neutra: o sinal diz se a parte encareceu ou barateou a conta. Verde e vermelho aqui
// contradiriam a tela de Receita, onde verde é a receita da empresa subindo.
function tom(valor: number) {
	return valor === 0 ? "text-text-muted" : "text-text";
}

/**
 * Por que a conta do mês de referência mudou contra a do mesmo mês do ano anterior, em R$
 * (DEC-052). As partes e a diferença vêm prontas da API e somam a diferença: a tela só mostra.
 */
export function VariacaoContaUc({ data }: { data: Uc360 }) {
	const variacao = data.variacao_conta;

	return (
		<section
			aria-labelledby="uc-variacao-conta"
			className="@container flex min-w-0 flex-col gap-3 rounded-md border border-border bg-surface-1 p-4"
		>
			<header>
				<div className="flex items-center gap-1.5">
					<h2 id="uc-variacao-conta" className="text-heading">
						Por que a conta mudou
					</h2>
					<Popover>
						<PopoverTrigger
							openOnHover
							delay={200}
							aria-label="Sobre a divisão da conta"
							className="grid size-6 place-items-center rounded-sm text-text-muted outline-none transition-colors hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50"
						>
							<InfoIcon aria-hidden className="size-3.5" />
						</PopoverTrigger>
						<PopoverContent className="max-w-80 p-3 text-body">
							<AjudaDasPartes comDias={variacao?.dias != null} />
						</PopoverContent>
					</Popover>
				</div>
				{variacao && (
					<p className="mt-1 text-small text-text-muted">
						{formatCompetencia(variacao.competencia)} comparada com{" "}
						{formatCompetencia(variacao.competencia_comparada)}
					</p>
				)}
			</header>
			{variacao ? (
				<CorpoVariacao variacao={variacao} />
			) : (
				<p className="text-small text-text-muted">
					Sem a conta do mesmo mês do ano anterior para comparar, ou ela não
					teve energia faturada (geração própria compensou o consumo).
				</p>
			)}
		</section>
	);
}

/**
 * O que é cada parte, como na DEC-052. Com "dias" separada, o consumo é o gasto por dia; sem
 * ela, o consumo leva toda a energia a mais ou a menos.
 */
function AjudaDasPartes({ comDias }: { comDias: boolean }) {
	return (
		<>
			<p className="mb-2">
				A diferença entre as duas contas, dividida por motivo. As partes somam
				exatamente a diferença.
			</p>
			<dl className="grid gap-1.5 text-small [&_dt]:font-medium [&_dt]:text-text">
				<div>
					<dt>Consumo</dt>
					<dd className="text-text-muted">
						{comDias
							? "O cliente gastou mais ou menos energia por dia, ao preço do ano anterior."
							: "O cliente gastou mais ou menos energia, ao preço do ano anterior."}
					</dd>
				</div>
				{comDias && (
					<div>
						<dt>Dias na fatura</dt>
						<dd className="text-text-muted">
							A conta cobriu mais ou menos dias, no consumo diário do ano
							anterior.
						</dd>
					</div>
				)}
				<div>
					<dt>Tarifa</dt>
					<dd className="text-text-muted">
						Reajuste da tarifa base por kWh, sem a bandeira. Fica também com a
						sobra de centavos do arredondamento.
					</dd>
				</div>
				<div>
					<dt>Bandeira</dt>
					<dd className="text-text-muted">
						Acréscimo da bandeira tarifária além do que a conta do ano anterior
						já cobrava por kWh.
					</dd>
				</div>
				<div>
					<dt>Tributos</dt>
					<dd className="text-text-muted">Variação dos impostos da conta.</dd>
				</div>
			</dl>
		</>
	);
}

function CorpoVariacao({
	variacao,
}: {
	variacao: NonNullable<Uc360["variacao_conta"]>;
}) {
	const partes = partesDaConta(variacao);
	const maior = maiorParte(partes, variacao.diferenca);
	const escala = Math.max(...partes.map((p) => Math.abs(p.valor)));

	return (
		<>
			{/* Cada conta com o seu mês: o atendente lê ao cliente qual conta é qual, sem depender da seta.
			    Na coluna estreita, a diferença desce para a linha de baixo. */}
			<dl className="grid grid-cols-2 gap-3 @sm:grid-cols-3 [&_dd]:mt-1 [&_dd]:font-mono [&_dd]:tabular-nums [&_dt]:text-small [&_dt]:text-text-muted">
				<div>
					<dt>Conta de {formatCompetencia(variacao.competencia_comparada)}</dt>
					<dd className="text-body">{formatBRL(variacao.conta_comparada)}</dd>
				</div>
				<div>
					<dt>Conta de {formatCompetencia(variacao.competencia)}</dt>
					<dd className="text-body">{formatBRL(variacao.conta)}</dd>
				</div>
				<div>
					<dt>Diferença</dt>
					<dd className={cn("text-body", tom(variacao.diferenca))}>
						{formatBRL(variacao.diferenca, { sinal: true })}
					</dd>
				</div>
			</dl>
			<p className="text-body text-text-muted">
				{variacao.diferenca === 0
					? "A conta não mudou."
					: `A conta ${variacao.diferenca > 0 ? "subiu" : "caiu"}.`}
				{maior && (
					<>
						{" "}
						O que mais pesou:{" "}
						<span className="text-text">{maior.rotulo.toLowerCase()}</span>{" "}
						<span className="text-text">
							({formatBRL(maior.valor, { sinal: true })})
						</span>
						.
					</>
				)}
			</p>
			<ul className={GRADE}>
				{partes.map((parte) => {
					const largura =
						escala > 0 ? (Math.abs(parte.valor) / escala) * 50 : 0;
					return (
						<li key={parte.id}>
							<span className="truncate text-body">{parte.rotulo}</span>
							{/* Eixo no meio: o que encarece cresce para a direita, o que barateia para a esquerda. */}
							<span aria-hidden className="relative">
								<span className="absolute inset-y-1.5 left-1/2 w-px bg-border-strong" />
								{largura > 0 && (
									<span
										className="absolute inset-y-2.75 rounded-sm bg-text-muted"
										style={
											parte.valor > 0
												? { left: "50%", width: `${largura}%` }
												: { right: "50%", width: `${largura}%` }
										}
									/>
								)}
							</span>
							<span
								className={cn(
									"justify-end font-mono text-small tabular-nums",
									tom(parte.valor),
								)}
							>
								{parte.valor === 0
									? "sem mudança"
									: formatBRL(parte.valor, { sinal: true })}
							</span>
						</li>
					);
				})}
			</ul>
			{variacao.leitura_estimada && (
				<p className="flex items-start gap-1.5 text-small text-warning">
					<WarningCircleIcon aria-hidden className="mt-0.5 size-4 shrink-0" />
					Uma das leituras foi estimada. A próxima leitura real corrige o
					consumo.
				</p>
			)}
		</>
	);
}
