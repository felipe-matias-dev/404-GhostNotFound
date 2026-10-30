import { getRouteApi } from "@tanstack/react-router";
import { Pagina } from "#/components/layout/pagina";
import { useSession } from "#/features/auth";
import type { Recorte } from "#/lib/filtros";
import { useMediaQuery } from "#/lib/use-media-query";
import { AcoesOrdemProvider, useAcoesOrdem } from "../components/acoes-ordem";
import { FilaSuspeitas } from "../components/fila-suspeitas";
import { GerarOrdens } from "../components/gerar-ordens";
import { OrdensKanban } from "../components/ordens-kanban";
import { OrdensTable } from "../components/ordens-table";
import { StatusFilter } from "../components/status-filter";
import { VisaoToggle } from "../components/visao-toggle";
import { useOrdens } from "../hooks/use-ordens";
import { useVisaoOrdens } from "../hooks/use-visao-ordens";
import { recorteDaBusca } from "../search";
import type { StatusOrdem } from "../types";

const route = getRouteApi("/perdas");

export function PerdasPage() {
	return (
		<AcoesOrdemProvider>
			<OrdensSecao />
		</AcoesOrdemProvider>
	);
}

function OrdensSecao() {
	const search = route.useSearch();
	const { status, secao: secaoParam } = search;
	const { data: user } = useSession();
	const recorte = recorteDaBusca(search);
	const canEdit = user?.perfil === "perdas";
	const navigate = route.useNavigate();
	const secao = secaoParam ?? (status ? "ordens" : "fila");
	const setSecao = (next: "fila" | "ordens") =>
		navigate({ search: (prev) => ({ ...prev, secao: next }) });
	const { visao, definirVisao } = useVisaoOrdens();
	// Abaixo de 48rem o Kanban não cabe: a tabela vira cards, sem mexer na preferência salva.
	const largo = useMediaQuery("(min-width: 48rem)");
	const visaoEfetiva = largo && canEdit ? visao : "tabela";

	const filtrar = (next: StatusOrdem | undefined) =>
		navigate({ search: (prev) => ({ ...prev, status: next }) });

	const kanban = visaoEfetiva === "kanban";

	return (
		<Pagina className="min-h-full max-w-none">
			<h1 className="sr-only">Perdas</h1>
			<nav
				aria-label="Seções de perdas"
				className="flex items-center gap-2 border-b border-border pb-4"
			>
				{(["fila", "ordens"] as const).map((item) => (
					<button
						key={item}
						type="button"
						aria-current={secao === item ? "page" : undefined}
						aria-controls={`perdas-${item}`}
						onClick={() => setSecao(item)}
						className={
							secao === item
								? "rounded-full border border-border-strong bg-surface-2 px-4 py-2 text-body font-medium text-text outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
								: "rounded-full border border-border bg-surface-1 px-4 py-2 text-body text-text-muted outline-none hover:bg-surface-2 hover:text-text focus-visible:ring-2 focus-visible:ring-focus-ring"
						}
					>
						{item === "fila" ? "Suspeitas" : "Inspeções"}
					</button>
				))}
			</nav>
			<div id="perdas-fila" hidden={secao !== "fila"}>
				<FilaSuspeitas onVerOrdens={() => setSecao("ordens")} />
			</div>
			<div
				id="perdas-ordens"
				hidden={secao !== "ordens"}
				className={secao === "ordens" ? "flex flex-1 flex-col" : undefined}
			>
				<section
					aria-labelledby="ordens-titulo"
					className={
						kanban ? "flex flex-1 flex-col gap-3" : "flex flex-col gap-3"
					}
				>
					<div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
						<div className="flex flex-wrap items-center gap-2">
							<h2 id="ordens-titulo" className="sr-only">
								Ordens de inspeção
							</h2>
							{canEdit && <GerarOrdens />}
							{largo && canEdit && (
								<VisaoToggle value={visao} onChange={definirVisao} />
							)}
						</div>
						{visaoEfetiva === "tabela" && (
							<StatusFilter value={status} onChange={filtrar} />
						)}
					</div>
					{kanban ? (
						<KanbanDasOrdens
							recorte={recorte}
							onVerTodas={(finalizada) => {
								definirVisao("tabela");
								filtrar(finalizada);
							}}
						/>
					) : (
						<OrdensTable status={status} recorte={recorte} />
					)}
				</section>
			</div>
		</Pagina>
	);
}

function KanbanDasOrdens({
	recorte,
	onVerTodas,
}: {
	recorte: Recorte;
	onVerTodas: (status: "CONCLUIDA" | "CANCELADA") => void;
}) {
	const { data, isPending, isError, refetch } = useOrdens(undefined, recorte);
	const { abrir, abrirHistorico, pendente } = useAcoesOrdem();

	return (
		<OrdensKanban
			ordens={data}
			loading={isPending}
			error={
				isError ? "Não foi possível carregar as ordens de inspeção." : null
			}
			onRetry={() => refetch()}
			onAcao={abrir}
			onHistorico={abrirHistorico}
			pendente={pendente}
			onVerTodas={onVerTodas}
		/>
	);
}
