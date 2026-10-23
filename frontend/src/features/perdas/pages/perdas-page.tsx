import { getRouteApi } from "@tanstack/react-router";
import { Pagina } from "#/components/layout/pagina";
import { OrdensTable } from "../components/ordens-table";
import { StatusFilter } from "../components/status-filter";

const route = getRouteApi("/perdas");

export function PerdasPage() {
	const { status } = route.useSearch();
	const navigate = route.useNavigate();

	return (
		<Pagina descricao="Fila de unidades consumidoras com suspeita de perda não técnica e as ordens de inspeção em campo.">
			<section aria-labelledby="ordens-titulo" className="flex flex-col gap-3">
				<div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
					<h2 id="ordens-titulo" className="text-heading">
						Ordens de inspeção
					</h2>
					<StatusFilter
						value={status}
						onChange={(next) =>
							navigate({ search: (prev) => ({ ...prev, status: next }) })
						}
					/>
				</div>
				<OrdensTable status={status} />
			</section>
		</Pagina>
	);
}
