import { getRouteApi } from "@tanstack/react-router";
import { Pagina } from "#/components/layout/pagina";
import { useSession } from "#/features/auth";
import { useMediaQuery } from "#/lib/use-media-query";
import { AcoesOrdemProvider, useAcoesOrdem } from "../components/acoes-ordem";
import { GerarOrdens } from "../components/gerar-ordens";
import { OrdensKanban } from "../components/ordens-kanban";
import { OrdensTable } from "../components/ordens-table";
import { StatusFilter } from "../components/status-filter";
import { VisaoToggle } from "../components/visao-toggle";
import { useOrdens } from "../hooks/use-ordens";
import { useVisaoOrdens } from "../hooks/use-visao-ordens";
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
	const { status } = route.useSearch();
	const { data: user } = useSession();
	const canEdit = user?.perfil === "perdas";
	const navigate = route.useNavigate();
	const { visao, definirVisao } = useVisaoOrdens();
	// Abaixo de 48rem o Kanban não cabe: a tabela vira cards, sem mexer na preferência salva.
	const largo = useMediaQuery("(min-width: 48rem)");
	const visaoEfetiva = largo && canEdit ? visao : "tabela";

	const filtrar = (next: StatusOrdem | undefined) =>
		navigate({ search: (prev) => ({ ...prev, status: next }) });

	const kanban = visaoEfetiva === "kanban";

	return (
		<Pagina className="min-h-full max-w-none">
			<section
				aria-labelledby="ordens-titulo"
				className={
					kanban ? "flex flex-1 flex-col gap-3" : "flex flex-col gap-3"
				}
			>
				<div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
					<div className="flex flex-wrap items-center gap-2">
						<h2 id="ordens-titulo" className="mr-2 text-heading">
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
						onVerTodas={(finalizada) => {
							definirVisao("tabela");
							filtrar(finalizada);
						}}
					/>
				) : (
					<OrdensTable status={status} />
				)}
			</section>
		</Pagina>
	);
}

function KanbanDasOrdens({
	onVerTodas,
}: {
	onVerTodas: (status: "CONCLUIDA" | "CANCELADA") => void;
}) {
	const { data, isPending, isError, refetch } = useOrdens(undefined);
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
