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

// Do ponto de vista do cliente: o que encarece a conta é alerta, o que barateia é alívio.
function tom(valor: number) {
	if (valor > 0) return { texto: "text-danger", barra: "bg-danger" };
	if (valor < 0) return { texto: "text-success", barra: "bg-success" };
	return { texto: "text-text-muted", barra: "" };
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
						<PopoverContent className="max-w-72 p-3 text-body">
							Diferença entre a conta do mês de referência e a do mesmo mês do
							ano anterior, dividida por motivo. Consumo é a energia a mais ou a
							menos, ao preço do ano anterior. Tarifa é o reajuste do preço por
							kWh, incluindo a sobra de centavos do arredondamento.
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

function CorpoVariacao({
	variacao,
}: {
	variacao: NonNullable<Uc360["variacao_conta"]>;
}) {
	const partes = partesDaConta(variacao);
	const maior = maiorParte(partes);
	const escala = Math.max(...partes.map((p) => Math.abs(p.valor)));
	const diferenca = tom(variacao.diferenca);

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
					<dd className={cn("text-body", diferenca.texto)}>
						{formatBRL(variacao.diferenca, { sinal: true })}
					</dd>
				</div>
			</dl>
			<p className="text-body text-text-muted">
				{variacao.diferenca === 0
					? "A conta não mudou."
					: `A conta ${variacao.diferenca > 0 ? "subiu" : "caiu"} ${formatBRL(Math.abs(variacao.diferenca))}.`}
				{maior && (
					<>
						{" "}
						O que mais pesou:{" "}
						<span className="text-text">{maior.rotulo.toLowerCase()}</span>{" "}
						<span className={tom(maior.valor).texto}>
							({formatBRL(maior.valor, { sinal: true })})
						</span>
						.
					</>
				)}
			</p>
			<ul className={GRADE}>
				{partes.map((parte) => {
					const t = tom(parte.valor);
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
										className={cn("absolute inset-y-2.75 rounded-sm", t.barra)}
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
									t.texto,
								)}
							>
								{formatBRL(parte.valor, { sinal: true })}
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
