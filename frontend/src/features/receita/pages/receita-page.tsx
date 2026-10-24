import { getRouteApi } from "@tanstack/react-router";
import { useState } from "react";
import { Pagina } from "#/components/layout/pagina";
import { DecomposicaoTable } from "../components/decomposicao-table";
import { MapaRecorte } from "../components/mapa-recorte";
import { RecorteTrilha } from "../components/recorte-trilha";
import type { DecomposicaoLinha, Recorte } from "../types";

const route = getRouteApi("/receita");

export function ReceitaPage() {
	const { municipio, bairro } = route.useSearch();
	const navigate = route.useNavigate();
	// Bairro sem município é recusado pela API (o mesmo nome existe em mais de um município).
	const recorte: Recorte = {
		municipio,
		bairro: municipio ? bairro : undefined,
	};
	const mudar = (proximo: Recorte) => navigate({ search: proximo });

	// Linha da tabela sob o ponteiro, contornada no mapa. Ao trocar de recorte, a linha some
	// sem disparar o "saiu" (a tabela troca de linhas): limpa aqui.
	const [destaque, setDestaque] = useState<DecomposicaoLinha | null>(null);
	const chaveRecorte = `${recorte.municipio ?? ""}|${recorte.bairro ?? ""}`;
	const [recorteAnterior, setRecorteAnterior] = useState(chaveRecorte);
	if (chaveRecorte !== recorteAnterior) {
		setRecorteAnterior(chaveRecorte);
		setDestaque(null);
	}

	return (
		<Pagina
			className="max-w-7xl"
			descricao="Ponte de receita entre dois períodos, separada em efeito preço, volume e mix, com drill-down por município, bairro e classe."
		>
			<RecorteTrilha recorte={recorte} onChange={mudar} />
			<div className="grid gap-5 lg:grid-cols-[17rem_minmax(0,1fr)] lg:items-start">
				<MapaRecorte
					recorte={recorte}
					destaque={destaque}
					onChange={mudar}
					className="h-80 lg:sticky lg:top-5 lg:h-[min(75svh,44rem)]"
				/>
				<section
					aria-labelledby="ponte-titulo"
					className="flex min-w-0 flex-col gap-3"
				>
					<h2 id="ponte-titulo" className="text-heading">
						Ponte de receita
					</h2>
					<DecomposicaoTable
						filtro={recorte}
						onAbrir={mudar}
						onDestaque={setDestaque}
					/>
				</section>
			</div>
		</Pagina>
	);
}
