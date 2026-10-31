import { getRouteApi } from "@tanstack/react-router";
import { useState } from "react";
import { Pagina } from "#/components/layout/pagina";
import { Button } from "#/components/ui/button";
import { useFiltrosPortal, usePeriodosDecomposicao } from "#/features/filtros";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { DecomposicaoTable } from "../components/decomposicao-table";
import { MapaRecorte } from "../components/mapa-recorte";
import { PonteWaterfall } from "../components/ponte-waterfall";
import { RankingQueda } from "../components/ranking-queda";
import type { Efeito } from "../conversions";
import type { DecomposicaoLinha } from "../types";

const route = getRouteApi("/receita");

export function ReceitaPage() {
	const { efeito } = route.useSearch();
	const { filtros, alterar } = useFiltrosPortal();
	const navigate = route.useNavigate();
	// A causa escolhida na ponte acompanha o drill-down e a troca de período.
	const causa: Efeito = efeito ?? "variacao";
	// Bairro sem município é recusado pela API (o mesmo nome existe em mais de um município).
	// A classe não é um nível: filtra todos ("como foi a B1 na RMR inteira?").
	const recorte: Recorte = {
		municipio: filtros.municipio,
		bairro: filtros.municipio ? filtros.bairro : undefined,
		classe: filtros.classe,
	};
	// O período da URL é soberano: a tela não troca por outro par gravado.
	const par: ParPeriodos | undefined =
		filtros.periodo_base && filtros.periodo_atual
			? {
					periodo_base: filtros.periodo_base,
					periodo_atual: filtros.periodo_atual,
				}
			: undefined;

	// O catálogo diz se a Gold gravou o par; sem ele não há ponte, mapa nem tabela.
	const periodos = usePeriodosDecomposicao();
	const parGravado = par
		? periodos.data?.some(
				(p) =>
					p.periodo_base === par.periodo_base &&
					p.periodo_atual === par.periodo_atual,
			) === true
		: false;

	// Mapa, ranking e tabela alteram o recorte compartilhado; período e `efeito` ficam como
	// estão. O provider limpa o bairro quando o município muda.
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
	const chaveRecorte = `${recorte.municipio ?? ""}|${recorte.bairro ?? ""}|${recorte.classe ?? ""}|${par?.periodo_base ?? ""}|${par?.periodo_atual ?? ""}`;
	const [recorteAnterior, setRecorteAnterior] = useState(chaveRecorte);
	if (chaveRecorte !== recorteAnterior) {
		setRecorteAnterior(chaveRecorte);
		setDestaque(null);
	}

	if (periodos.isPending) {
		return (
			<Pagina className="max-w-none">
				<p className="text-text-muted">Carregando os períodos da receita…</p>
			</Pagina>
		);
	}

	if (periodos.isError) {
		return (
			<Pagina className="max-w-none">
				<div className="flex flex-col items-start gap-2">
					<p className="text-text-muted">
						Não foi possível carregar os períodos da decomposição de receita.
					</p>
					<Button
						variant="outline"
						size="sm"
						onClick={() => {
							void periodos.refetch();
						}}
					>
						Tentar novamente
					</Button>
				</div>
			</Pagina>
		);
	}

	if (!periodos.data?.length) {
		return (
			<Pagina className="max-w-none">
				<p className="text-text-muted">
					Sem dados de decomposição de receita: a Gold não tem nenhum par de
					períodos gravado.
				</p>
			</Pagina>
		);
	}

	if (!par) {
		return (
			<Pagina className="max-w-none">
				<p className="text-text-muted">
					Selecione um período para ver a decomposição de receita.
				</p>
			</Pagina>
		);
	}

	if (!parGravado) {
		return (
			<Pagina className="max-w-none">
				<p className="text-text-muted">
					A decomposição de receita não está disponível para os períodos
					selecionados.
				</p>
			</Pagina>
		);
	}

	return (
		<Pagina className="max-w-none">
			<div className="grid gap-5 lg:grid-cols-[clamp(20rem,26%,28rem)_minmax(0,1fr)] lg:items-start">
				<MapaRecorte
					par={par}
					recorte={recorte}
					efeito={causa}
					destaque={destaque}
					onChange={alterar}
					className="h-96 lg:sticky lg:top-5 lg:h-[calc(100svh-8rem)]"
				/>
				<section
					aria-label="Decomposição de receita"
					className="@container flex min-w-0 flex-col gap-3"
				>
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
							onAbrir={alterar}
							onDestaque={setDestaque}
						/>
					</div>
					<DecomposicaoTable
						par={par}
						filtro={recorte}
						efeito={causa}
						onAbrir={alterar}
						onDestaque={setDestaque}
					/>
				</section>
			</div>
		</Pagina>
	);
}
