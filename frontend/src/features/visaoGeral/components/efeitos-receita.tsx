import {
	ArrowsClockwiseIcon,
	InfoIcon,
	XCircleIcon,
} from "@phosphor-icons/react";
import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Button } from "#/components/ui/button";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "#/components/ui/popover";
import { useFiltrosPortal, usePeriodosDecomposicao } from "#/features/filtros";
import {
	EFEITOS,
	passosDaPonte,
	useDecomposicao,
} from "#/features/receita";
import { formatPct, formatPeriodoCurto } from "#/lib/format";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { cn } from "#/lib/utils";
import { efeitosDaReceita } from "../conversions";

// Rótulo, barra e valor juntos: a barra não atravessa a coluna até o número.
const LINHA =
	"grid h-9 grid-cols-[8rem_minmax(0,20rem)_3.5rem] items-center gap-4";

function Molde() {
	return (
		<ul aria-hidden className="grid gap-x-12 gap-y-1 md:grid-cols-2">
			{["w-1/3", "w-1/5", "w-1/5", "w-1/12"].map((largura, i) => (
				<li
					// biome-ignore lint/suspicious/noArrayIndexKey: linhas fixas do molde.
					key={i}
					className={LINHA}
				>
					<div className="h-3 w-20 rounded-sm bg-pressed" />
					<div className={cn("h-2.5 rounded-sm bg-pressed", largura)} />
					<div className="h-3 w-10 justify-self-end rounded-sm bg-pressed" />
				</li>
			))}
		</ul>
	);
}

function Falha({ texto, retry }: { texto: string; retry: () => void }) {
	return (
		<div className="flex flex-col items-start gap-2">
			<p className="flex items-center gap-1.5 text-body">
				<XCircleIcon aria-hidden className="size-4 shrink-0 text-danger" />
				{texto}
			</p>
			<Button variant="ghost" size="xs" className="-ml-1.5" onClick={retry}>
				<ArrowsClockwiseIcon aria-hidden />
				Tentar de novo
			</Button>
		</div>
	);
}

/**
 * O porquê da tesoura: o peso de cada efeito da ponte de receita (tarifa, bandeira, volume e mix)
 * no mesmo par e recorte da barra comum. Cada linha abre a ponte com o efeito escolhido. Sem o
 * par gravado na Gold, o bloco explica a indisponibilidade; falha de rede continua sendo erro.
 */
export function EfeitosReceita({
	par,
	recorte,
	carregando,
	semPeriodo,
}: {
	par: ParPeriodos | undefined;
	recorte: Recorte;
	/** O período padrão ainda não foi resolvido pela barra comum. */
	carregando: boolean;
	/** A Gold não tem dois meses para comparar: o período ainda não foi escolhido. */
	semPeriodo: boolean;
}) {
	const { searchPara } = useFiltrosPortal();
	const periodos = usePeriodosDecomposicao();
	const gravado = Boolean(
		par &&
			periodos.data?.some(
				(p) =>
					p.periodo_base === par.periodo_base &&
					p.periodo_atual === par.periodo_atual,
			),
	);
	const decomposicao = useDecomposicao(gravado ? par : undefined, recorte);

	const efeitos = decomposicao.data
		? efeitosDaReceita(passosDaPonte(decomposicao.data))
		: undefined;
	const maior = Math.max(...(efeitos ?? []).map((e) => Math.abs(e.pct ?? 0)));

	let corpo: ReactNode;
	if (semPeriodo) {
		corpo = (
			<p className="text-pretty text-body text-text-muted">
				Escolha um período na barra de filtros para ver os efeitos da receita.
			</p>
		);
	} else if (periodos.isError) {
		corpo = (
			<Falha
				texto="Não foi possível carregar os efeitos da receita."
				retry={() => void periodos.refetch()}
			/>
		);
	} else if (carregando || periodos.isPending) {
		corpo = <Molde />;
	} else if (!gravado) {
		corpo = (
			<p className="text-pretty text-body text-text-muted">
				A decomposição de receita não está disponível para os períodos
				selecionados.
			</p>
		);
	} else if (decomposicao.isError) {
		corpo = (
			<Falha
				texto="Não foi possível carregar os efeitos da receita."
				retry={() => void decomposicao.refetch()}
			/>
		);
	} else if (decomposicao.isPlaceholderData || !efeitos) {
		corpo = <Molde />;
	} else if (efeitos.length === 0) {
		corpo = (
			<p className="text-pretty text-body text-text-muted">
				Sem efeitos de receita para o recorte selecionado.
			</p>
		);
	} else {
		corpo = (
			<ul className="grid gap-x-12 gap-y-1 md:grid-cols-2">
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
								search={
									searchPara("/receita", {
										efeito: EFEITOS.find((e) => e === efeito.id),
									}) as never
								}
								aria-label={`${efeito.rotulo}: ${texto} sobre a receita base. Abrir na ponte de receita`}
								className={cn(
									LINHA,
									"-mx-2 rounded-sm px-2 outline-none transition-colors hover:bg-hover focus-visible:ring-3 focus-visible:ring-focus-ring/50",
								)}
							>
								<span className="truncate text-body text-text">
									{efeito.rotulo}
								</span>
								{/* Eixo no meio: alta cresce para a direita, queda para a esquerda. */}
								<span aria-hidden className="relative h-2.5">
									<span className="-inset-y-1 absolute left-1/2 w-px bg-border-strong" />
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
			className="flex flex-col gap-3 rounded-md border border-border bg-surface-1 p-5 shadow-edge"
		>
			<header className="flex items-center gap-1.5">
				<h2 id="efeitos-titulo" className="text-heading">
					Por que a receita mudou
				</h2>
				<Popover>
					<PopoverTrigger
						openOnHover
						delay={200}
						aria-label="Sobre os efeitos da receita"
						className="grid size-6 place-items-center rounded-sm text-text-muted outline-none transition-colors hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50"
					>
						<InfoIcon aria-hidden className="size-3.5" />
					</PopoverTrigger>
					<PopoverContent className="max-w-64 p-3 text-body">
						Peso de cada efeito sobre a receita de energia de{" "}
						{formatPeriodoCurto(par?.periodo_base)}. Clique num efeito para vê-lo
						na ponte de receita.
					</PopoverContent>
				</Popover>
			</header>
			{corpo}
		</section>
	);
}
