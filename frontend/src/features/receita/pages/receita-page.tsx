import { getRouteApi } from "@tanstack/react-router";
import { useState } from "react";
import { Pagina } from "#/components/layout/pagina";
import { DecomposicaoTable } from "../components/decomposicao-table";
import { MapaRecorte } from "../components/mapa-recorte";
import { PeriodoPicker } from "../components/periodo-picker";
import { PonteWaterfall } from "../components/ponte-waterfall";
import { RankingQueda } from "../components/ranking-queda";
import { RecorteTrilha } from "../components/recorte-trilha";
import { type Efeito, parPadrao } from "../conversions";
import { usePeriodosDecomposicao } from "../hooks/use-decomposicao";
import type { DecomposicaoLinha, ParPeriodos, Recorte } from "../types";

const route = getRouteApi("/receita");

export function ReceitaPage() {
	const { municipio, bairro, periodo_base, periodo_atual, efeito } =
		route.useSearch();
	// A causa escolhida na ponte acompanha o drill-down e a troca de período.
	const causa: Efeito = efeito ?? "variacao";
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

	// Mapa, trilha e tabela só conhecem município e bairro: a causa segue da URL.
	const navegar = (proximo: Recorte, comPar: ParPeriodos | undefined) =>
		navigate({
			search: {
				municipio: proximo.municipio,
				bairro: proximo.bairro,
				periodo_base: comPar?.periodo_base,
				periodo_atual: comPar?.periodo_atual,
				efeito,
			},
		});
	const mudar = (proximo: Recorte) => navegar(proximo, par);
	const escolherCausa = (proxima: Efeito) =>
		navigate({
			search: (atual) => ({
				...atual,
				efeito: proxima === "variacao" ? undefined : proxima,
			}),
			resetScroll: false,
		});

	// Linha da tabela sob o ponteiro, contornada no mapa. Ao trocar de recorte ou de período,
	// a linha some sem disparar o "saiu" (a tabela troca de linhas): limpa aqui.
	const [destaque, setDestaque] = useState<DecomposicaoLinha | null>(null);
	const chaveRecorte = `${recorte.municipio ?? ""}|${recorte.bairro ?? ""}|${par?.periodo_base ?? ""}|${par?.periodo_atual ?? ""}`;
	const [recorteAnterior, setRecorteAnterior] = useState(chaveRecorte);
	if (chaveRecorte !== recorteAnterior) {
		setRecorteAnterior(chaveRecorte);
		setDestaque(null);
	}

	// Sem pares, a consulta da decomposição nunca liga e a tabela ficaria carregando.
	if (periodos.isError || periodos.data?.length === 0) {
		return (
			<Pagina className="max-w-none">
				<p className="text-text-muted">
					{periodos.isError
						? "Não foi possível carregar os períodos da decomposição de receita."
						: "Sem dados de decomposição de receita: a Gold não tem nenhum par de períodos gravado."}
				</p>
			</Pagina>
		);
	}

	return (
		<Pagina className="max-w-none">
			<RecorteTrilha par={par} recorte={recorte} onChange={mudar} />
			<div className="grid gap-5 lg:grid-cols-[clamp(20rem,26%,28rem)_minmax(0,1fr)] lg:items-start">
				<MapaRecorte
					par={par}
					recorte={recorte}
					efeito={causa}
					destaque={destaque}
					onChange={mudar}
					className="h-96 lg:sticky lg:top-5 lg:h-[calc(100svh-8rem)]"
				/>
				<section
					aria-labelledby="ponte-titulo"
					className="@container flex min-w-0 flex-col gap-3"
				>
					<div className="flex flex-wrap items-center justify-between gap-2">
						<h2 id="ponte-titulo" className="text-heading">
							Ponte de receita
						</h2>
						<PeriodoPicker
							pares={periodos.data ?? []}
							par={par}
							onEscolher={(escolhido) => navegar(recorte, escolhido)}
						/>
					</div>
					{/* Largo: ponte e ranking lado a lado, sem a ponte esticar por toda a largura. */}
					<div className="grid gap-3 @4xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.8fr)]">
						<PonteWaterfall
							par={par}
							recorte={recorte}
							efeito={causa}
							onEfeito={escolherCausa}
						/>
						<RankingQueda
							par={par}
							recorte={recorte}
							efeito={causa}
							onEfeito={escolherCausa}
							onAbrir={mudar}
							onDestaque={setDestaque}
						/>
					</div>
					<DecomposicaoTable
						par={par}
						filtro={recorte}
						efeito={causa}
						onAbrir={mudar}
						onDestaque={setDestaque}
					/>
				</section>
			</div>
		</Pagina>
	);
}
