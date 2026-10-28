import { ArrowsClockwiseIcon, CaretRightIcon } from "@phosphor-icons/react";
import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Button } from "#/components/ui/button";
import {
	EFEITOS,
	passosDaPonte,
	useDecomposicao,
	usePeriodosDecomposicao,
} from "#/features/receita";
import { formatPct, formatPeriodoCurto } from "#/lib/format";
import { cn } from "#/lib/utils";
import { efeitosDaReceita, type Janelas } from "../conversions";

const SEM_RECORTE = {};

function Molde() {
	return (
		<ul aria-hidden className="flex flex-col gap-1">
			{["w-1/3", "w-1/5", "w-1/5", "w-1/12"].map((largura, i) => (
				<li
					// biome-ignore lint/suspicious/noArrayIndexKey: linhas fixas do molde.
					key={i}
					className="grid h-10 grid-cols-[7.5rem_minmax(0,1fr)_3.5rem] items-center gap-4 sm:grid-cols-[9rem_minmax(0,1fr)_4rem]"
				>
					<div className="h-3 w-20 rounded-sm bg-pressed" />
					<div className={cn("h-2.5 rounded-sm bg-pressed", largura)} />
					<div className="h-3 w-10 justify-self-end rounded-sm bg-pressed" />
				</li>
			))}
		</ul>
	);
}

/**
 * O porquê da tesoura: o peso de cada efeito da ponte de receita (tarifa, bandeira, volume e mix)
 * no mesmo par de 12 meses do resumo. Cada linha abre a ponte com o efeito escolhido. Sem o par
 * gravado na Gold, o bloco não aparece.
 */
export function EfeitosReceita({ janelas }: { janelas: Janelas | undefined }) {
	const periodos = usePeriodosDecomposicao();
	const par = janelas
		? periodos.data?.find(
				(p) =>
					p.periodo_base === janelas.base && p.periodo_atual === janelas.atual,
			)
		: undefined;
	const decomposicao = useDecomposicao(par, SEM_RECORTE);

	if (!janelas || (periodos.data && !par)) return null;

	const efeitos = decomposicao.data
		? efeitosDaReceita(passosDaPonte(decomposicao.data))
		: undefined;
	const maior = Math.max(...(efeitos ?? []).map((e) => Math.abs(e.pct ?? 0)));

	let corpo: ReactNode;
	if (periodos.isError || decomposicao.isError) {
		corpo = (
			<div className="flex flex-col items-start gap-2">
				<p className="text-body text-text-muted">
					Não foi possível carregar os efeitos da receita.
				</p>
				<Button
					variant="ghost"
					size="xs"
					className="-ml-1.5"
					onClick={() =>
						periodos.isError ? periodos.refetch() : decomposicao.refetch()
					}
				>
					<ArrowsClockwiseIcon aria-hidden />
					Tentar de novo
				</Button>
			</div>
		);
	} else if (!efeitos) {
		corpo = <Molde />;
	} else {
		corpo = (
			<ul className="flex flex-col gap-1">
				{efeitos.map((efeito) => {
					const pct = efeito.pct ?? 0;
					const largura = maior > 0 ? (Math.abs(pct) / maior) * 50 : 0;
					const texto = formatPct(efeito.pct, { sinal: true });
					const tom = texto.startsWith("+")
						? "up"
						: texto.startsWith("-") || texto.startsWith("−")
							? "down"
							: "flat";
					return (
						<li key={efeito.id}>
							<Link
								to="/receita"
								search={{
									periodo_base: janelas.base,
									periodo_atual: janelas.atual,
									efeito: EFEITOS.find((e) => e === efeito.id),
								}}
								aria-label={`${efeito.rotulo}: ${texto} sobre a receita base. Abrir na ponte de receita`}
								className="group -mx-2 grid h-10 grid-cols-[7.5rem_minmax(0,1fr)_3.5rem_auto] items-center gap-4 rounded-sm px-2 outline-none transition-colors hover:bg-hover focus-visible:ring-3 focus-visible:ring-focus-ring/50 sm:grid-cols-[9rem_minmax(0,1fr)_4rem_auto]"
							>
								<span className="truncate text-body text-text">
									{efeito.rotulo}
								</span>
								{/* Eixo no meio: alta cresce para a direita, queda para a esquerda. */}
								<span aria-hidden className="relative h-2.5">
									<span className="absolute inset-y-[-3px] left-1/2 w-px bg-border-strong" />
									{largura > 0 ? (
										<span
											className={cn(
												"absolute inset-y-0 rounded-sm",
												tom === "up" ? "bg-success" : "bg-danger",
											)}
											style={
												pct >= 0
													? { left: "50%", width: `${largura}%` }
													: { right: "50%", width: `${largura}%` }
											}
										/>
									) : null}
								</span>
								<span
									aria-hidden
									className={cn(
										"text-right text-small tabular-nums",
										tom === "up" && "text-success",
										tom === "down" && "text-danger",
										tom === "flat" && "text-text-muted",
									)}
								>
									{texto}
								</span>
								<CaretRightIcon
									aria-hidden
									className="size-3.5 text-text-muted transition-[color,translate] group-hover:translate-x-0.5 group-hover:text-text motion-reduce:transition-none"
								/>
							</Link>
						</li>
					);
				})}
			</ul>
		);
	}

	return (
		<section
			aria-labelledby="efeitos-titulo"
			aria-busy={decomposicao.isFetching || undefined}
			className="flex max-w-3xl flex-col gap-3"
		>
			<header className="flex flex-col gap-1">
				<h2 id="efeitos-titulo" className="text-heading">
					Por que a receita mudou
				</h2>
				<p className="text-pretty text-small text-text-muted">
					Peso de cada efeito sobre a receita de energia de{" "}
					{formatPeriodoCurto(janelas.base)}.
				</p>
			</header>
			{corpo}
		</section>
	);
}
