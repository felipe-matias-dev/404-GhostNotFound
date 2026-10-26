import { getRouteApi } from "@tanstack/react-router";
import { useState } from "react";
import { Pagina } from "#/components/layout/pagina";
import { DecomposicaoTable } from "../components/decomposicao-table";
import { MapaRecorte } from "../components/mapa-recorte";
import { PeriodoMenu } from "../components/periodo-menu";
import { RecorteTrilha } from "../components/recorte-trilha";
import { parPadrao } from "../conversions";
import { usePeriodosDecomposicao } from "../hooks/use-decomposicao";
import type { DecomposicaoLinha, ParPeriodos, Recorte } from "../types";

const route = getRouteApi("/receita");

export function ReceitaPage() {
	const { municipio, bairro, periodo_base, periodo_atual } = route.useSearch();
	const navigate = route.useNavigate();
	// Bairro sem município é recusado pela API (o mesmo nome existe em mais de um município).
	const recorte: Recorte = {
		municipio,
		bairro: municipio ? bairro : undefined,
	};

	// O par da URL só vale se a Gold o gravou; senão, o padrão.
	const periodos = usePeriodosDecomposicao();
	const par =
		periodos.data?.find(
			(p) =>
				p.periodo_base === periodo_base && p.periodo_atual === periodo_atual,
		) ?? (periodos.data ? parPadrao(periodos.data) : undefined);

	const navegar = (proximo: Recorte, comPar: ParPeriodos | undefined) =>
		navigate({
			search: {
				...proximo,
				periodo_base: comPar?.periodo_base,
				periodo_atual: comPar?.periodo_atual,
			},
		});
	const mudar = (proximo: Recorte) => navegar(proximo, par);

	// Linha da tabela sob o ponteiro, contornada no mapa. Ao trocar de recorte ou de período,
	// a linha some sem disparar o "saiu" (a tabela troca de linhas): limpa aqui.
	const [destaque, setDestaque] = useState<DecomposicaoLinha | null>(null);
	const chaveRecorte = `${recorte.municipio ?? ""}|${recorte.bairro ?? ""}|${par?.periodo_base ?? ""}|${par?.periodo_atual ?? ""}`;
	const [recorteAnterior, setRecorteAnterior] = useState(chaveRecorte);
	if (chaveRecorte !== recorteAnterior) {
		setRecorteAnterior(chaveRecorte);
		setDestaque(null);
	}

	const descricao =
		"Ponte de receita entre dois períodos, separada em efeito preço, volume e mix, com drill-down por município, bairro e classe.";

	// Sem pares, a consulta da decomposição nunca liga e a tabela ficaria carregando.
	if (periodos.isError || periodos.data?.length === 0) {
		return (
			<Pagina className="max-w-7xl" descricao={descricao}>
				<p className="text-text-muted">
					{periodos.isError
						? "Não foi possível carregar os períodos da decomposição de receita."
						: "Sem dados de decomposição de receita: a Gold não tem nenhum par de períodos gravado."}
				</p>
			</Pagina>
		);
	}

	return (
		<Pagina className="max-w-7xl" descricao={descricao}>
			<RecorteTrilha par={par} recorte={recorte} onChange={mudar} />
			<div className="grid gap-5 lg:grid-cols-[17rem_minmax(0,1fr)] lg:items-start">
				<MapaRecorte
					par={par}
					recorte={recorte}
					destaque={destaque}
					onChange={mudar}
					className="h-80 lg:sticky lg:top-5 lg:h-[min(75svh,44rem)]"
				/>
				<section
					aria-labelledby="ponte-titulo"
					className="flex min-w-0 flex-col gap-3"
				>
					<div className="flex flex-wrap items-center justify-between gap-2">
						<h2 id="ponte-titulo" className="text-heading">
							Ponte de receita
						</h2>
						<PeriodoMenu
							pares={periodos.data ?? []}
							par={par}
							onEscolher={(escolhido) => navegar(recorte, escolhido)}
						/>
					</div>
					<DecomposicaoTable
						par={par}
						filtro={recorte}
						onAbrir={mudar}
						onDestaque={setDestaque}
					/>
				</section>
			</div>
		</Pagina>
	);
}
