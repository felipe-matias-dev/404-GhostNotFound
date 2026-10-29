import {
	getRouteApi,
	useLocation,
	useRouterState,
} from "@tanstack/react-router";
import { useEffect, useMemo, useRef } from "react";
import { Pagina } from "#/components/layout/pagina";
import {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbLink,
	BreadcrumbList,
	BreadcrumbPage,
	BreadcrumbSeparator,
} from "#/components/ui/breadcrumb";
import { Button } from "#/components/ui/button";
import {
	SegmentedControl,
	type SegmentedOption,
} from "#/components/ui/segmented-control";
import { useCompetencias } from "#/features/visaoGeral";
import { AlimentadorSheet } from "../components/alimentador-sheet";
import { ContinuidadeTable } from "../components/continuidade-table";
import { IntervaloMeses } from "../components/intervalo-meses";
import { linhasDoRanking, resolverPeriodo } from "../conversions";
import {
	useRankingContinuidade,
	useRecortesContinuidade,
	useSerieAlimentador,
} from "../hooks/use-continuidade";
import type { RedeSearch } from "../search";
import type {
	Criterio,
	LinhaContinuidade,
	NivelRecorte,
	Periodo,
	VisaoRede,
} from "../types";

const route = getRouteApi("/rede");

const VISOES: readonly SegmentedOption<VisaoRede>[] = [
	{ value: "alimentadores", label: "Alimentadores" },
	{ value: "localidades", label: "Localidades" },
];

const CRITERIOS: readonly SegmentedOption<Criterio>[] = [
	{ value: "dec", label: "DEC" },
	{ value: "fec", label: "FEC" },
];

const SEM_PERIODO =
	"Sem competências disponíveis. Escolha um período para consultar a continuidade.";
const FALHA_CALENDARIO = "Não foi possível carregar as competências.";

export function RedePage() {
	const search = route.useSearch();
	const navigate = route.useNavigate();

	// O calendário é o mesmo da Visão geral; a URL completa e válida vale mesmo fora dele.
	const competencias = useCompetencias();
	const periodo = resolverPeriodo(search, competencias.data ?? []);
	const padrao = resolverPeriodo({}, competencias.data ?? []);

	const criterio: Criterio = search.criterio ?? "dec";
	const visao: VisaoRede = search.visao ?? "alimentadores";
	const alimentador = search.alimentador;
	const metrica: Criterio = search.serie ?? criterio;
	const municipio = visao === "localidades" ? search.municipio : undefined;
	const bairro = visao === "localidades" ? search.bairro : undefined;

	// Hooks em ordem fixa; a consulta da visão inativa fica desligada por skipToken.
	const ranking = useRankingContinuidade(
		periodo,
		criterio,
		visao === "alimentadores",
	);
	const recortes = useRecortesContinuidade(
		periodo,
		criterio,
		{ municipio, bairro },
		visao === "localidades",
	);
	const serie = useSerieAlimentador(periodo, alimentador);

	const ativa = visao === "alimentadores" ? ranking : recortes;
	const rows: LinhaContinuidade[] | undefined =
		visao === "alimentadores"
			? ranking.data
				? linhasDoRanking(ranking.data)
				: undefined
			: recortes.data?.recortes;
	const n_meses =
		visao === "alimentadores" ? ranking.data?.n_meses : recortes.data?.n_meses;

	// O nível exibido é o da resposta; a URL só desenha o molde enquanto ela não chega.
	const nivelEsperado: NivelRecorte = bairro
		? "alimentador"
		: municipio
			? "bairro"
			: "municipio";
	const nivel: NivelRecorte =
		visao === "alimentadores"
			? "alimentador"
			: (recortes.data?.nivel ?? nivelEsperado);

	const titulo =
		visao === "alimentadores"
			? "Alimentadores"
			: bairro
				? `Alimentadores em ${bairro}`
				: municipio
					? `Bairros de ${municipio}`
					: "Municípios";

	// A forma canônica da tela: período resolvido, padrões omitidos e campos sem sentido fora.
	const alvo = useMemo<RedeSearch>(
		() => ({
			inicio: periodo?.inicio,
			fim: periodo?.fim,
			criterio: criterio === "dec" ? undefined : criterio,
			visao: visao === "localidades" ? "localidades" : undefined,
			municipio,
			bairro,
			alimentador,
			serie: alimentador ? metrica : undefined,
		}),
		[
			periodo?.inicio,
			periodo?.fim,
			criterio,
			visao,
			municipio,
			bairro,
			alimentador,
			metrica,
		],
	);
	const temPeriodo = Boolean(periodo);

	// A URL bruta ainda pode trazer campos que o schema já descartou (bairro órfão, série sem
	// alimentador, mês inválido): comparar só com o search validado esconderia esses casos.
	const buscaBruta = useLocation({
		select: (local) => local.search,
	}) as Record<string, unknown>;
	const canonica = Object.fromEntries(
		Object.entries(alvo).filter(([, valor]) => valor !== undefined),
	) as Record<string, string>;
	const precisaNormalizar =
		Object.keys(buscaBruta).length !== Object.keys(canonica).length ||
		Object.entries(canonica).some(
			([campo, valor]) => buscaBruta[campo] !== valor,
		);

	const tituloRef = useRef<HTMLHeadingElement>(null);
	const opener = useRef<HTMLElement | null>(null);
	const abertoAnterior = useRef(Boolean(alimentador));

	// Sem período não há padrão a gravar; com ele, a URL bruta fora da forma canônica é trocada.
	// Durante uma navegação a URL bruta anda à frente do search validado: normalizar ali
	// desfaria a ação do usuário.
	const navegando = useRouterState({ select: (estado) => estado.isLoading });
	useEffect(() => {
		if (!temPeriodo || navegando || !precisaNormalizar) return;
		void navigate({
			to: "/rede",
			search: alvo,
			replace: true,
			resetScroll: false,
		});
	}, [temPeriodo, navegando, precisaNormalizar, alvo, navigate]);

	const ir = (proximo: Partial<RedeSearch>, replace = false) =>
		navigate({
			to: "/rede",
			search: { ...alvo, ...proximo },
			replace,
			resetScroll: false,
		});

	const escolherVisao = (proxima: VisaoRede) =>
		void ir({
			visao: proxima === "localidades" ? "localidades" : undefined,
			municipio: undefined,
			bairro: undefined,
			alimentador: undefined,
			serie: undefined,
		});

	const escolherCriterio = (proximo: Criterio) =>
		void ir({ criterio: proximo === "dec" ? undefined : proximo });

	const escolherPeriodo = (proximo: Periodo) =>
		void ir({
			inicio: proximo.inicio,
			fim: proximo.fim,
			alimentador: undefined,
			serie: undefined,
		});

	// Abrir a linha grava o nível que a resposta atual oferece, nunca o da resposta anterior.
	const abrirLinha = (linha: LinhaContinuidade) => {
		const atual =
			visao === "alimentadores" ? "alimentador" : recortes.data?.nivel;
		if (!atual) return;
		const ativo = document.activeElement;
		opener.current =
			ativo instanceof HTMLElement && ativo !== document.body ? ativo : null;
		if (atual === "municipio") {
			void ir({
				visao: "localidades",
				municipio: linha.segmento,
				bairro: undefined,
				alimentador: undefined,
				serie: undefined,
			});
			return;
		}
		if (atual === "bairro") {
			void ir({
				visao: "localidades",
				bairro: linha.segmento,
				alimentador: undefined,
				serie: undefined,
			});
			return;
		}
		void ir({ alimentador: linha.segmento, serie: criterio });
	};

	const trocarSerie = (proximo: Criterio) => void ir({ serie: proximo }, true);

	// Fechar remove só o alimentador e a métrica do painel; tabela, recorte, período e página ficam.
	const fecharPainel = () =>
		void ir({ alimentador: undefined, serie: undefined });

	// O kit devolve o foco a quem abriu; sem ele (deep link, card desmontado), vai ao título.
	useEffect(() => {
		const aberto = Boolean(alimentador);
		if (abertoAnterior.current && !aberto) {
			const ativo = document.activeElement;
			const precisa =
				!ativo ||
				ativo === document.body ||
				(ativo instanceof HTMLElement &&
					ativo.closest('[data-slot^="sheet"]') !== null);
			if (precisa) {
				const destino = opener.current?.isConnected
					? opener.current
					: tituloRef.current;
				destino?.focus();
			}
			opener.current = null;
		}
		abertoAnterior.current = aberto;
	}, [alimentador]);

	const carregando = ativa.isLoading || (!periodo && competencias.isPending);
	const atualizando = ativa.isFetching && !ativa.isLoading;
	const erroTabela = ativa.isError
		? "Não foi possível carregar a continuidade deste recorte."
		: null;

	const semPeriodo = !periodo;
	const calendarioFalhou = semPeriodo && competencias.isError;
	const calendarioVazio =
		semPeriodo &&
		!competencias.isPending &&
		!competencias.isError &&
		(competencias.data?.length ?? 0) === 0;

	const legenda =
		n_meses === undefined
			? "Maiores índices primeiro"
			: `Maiores índices primeiro · ${n_meses} ${n_meses === 1 ? "mês" : "meses"} com dados na base`;

	return (
		<Pagina className="max-w-none">
			{visao === "localidades" && (
				<Breadcrumb aria-label="Recorte da rede">
					<BreadcrumbList>
						<BreadcrumbItem className="min-w-0">
							{municipio ? (
								<BreadcrumbLink
									render={
										<button
											type="button"
											onClick={() => escolherVisao("localidades")}
										/>
									}
								>
									Todos os municípios
								</BreadcrumbLink>
							) : (
								<BreadcrumbPage>Todos os municípios</BreadcrumbPage>
							)}
						</BreadcrumbItem>
						{municipio && (
							<>
								<BreadcrumbSeparator />
								<BreadcrumbItem className="min-w-0">
									{bairro ? (
										<BreadcrumbLink
											render={
												<button
													type="button"
													onClick={() =>
														void ir({
															bairro: undefined,
															alimentador: undefined,
															serie: undefined,
														})
													}
												/>
											}
										>
											{municipio}
										</BreadcrumbLink>
									) : (
										<BreadcrumbPage>{municipio}</BreadcrumbPage>
									)}
								</BreadcrumbItem>
							</>
						)}
						{bairro && (
							<>
								<BreadcrumbSeparator />
								<BreadcrumbItem className="min-w-0">
									<BreadcrumbPage>{bairro}</BreadcrumbPage>
								</BreadcrumbItem>
							</>
						)}
					</BreadcrumbList>
				</Breadcrumb>
			)}

			<section
				aria-labelledby="rede-titulo"
				className="flex min-w-0 flex-col gap-3"
			>
				<div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
					<div className="flex min-w-0 flex-col gap-1">
						<h2
							id="rede-titulo"
							ref={tituloRef}
							tabIndex={-1}
							className="text-heading rounded-sm outline-none focus-visible:ring-3 focus-visible:ring-focus-ring/50"
						>
							{titulo}
						</h2>
						<p className="text-small text-text-muted">{legenda}</p>
					</div>
					<div className="flex flex-wrap items-center gap-2">
						<SegmentedControl
							label="Visão da rede"
							value={visao}
							onValueChange={escolherVisao}
							options={VISOES}
						/>
						<IntervaloMeses
							periodo={periodo}
							padrao={padrao}
							onChange={escolherPeriodo}
						/>
						<SegmentedControl
							label="Critério da tabela"
							value={criterio}
							onValueChange={escolherCriterio}
							options={CRITERIOS}
						/>
					</div>
				</div>

				{calendarioFalhou && (
					<div
						role="alert"
						className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-danger/40 bg-danger-subtle p-3"
					>
						<p className="text-body text-danger">{FALHA_CALENDARIO}</p>
						<Button
							variant="outline"
							size="sm"
							onClick={() => void competencias.refetch()}
						>
							Tentar de novo
						</Button>
					</div>
				)}

				{calendarioVazio && (
					<p className="text-body text-text-muted">{SEM_PERIODO}</p>
				)}

				{(periodo || competencias.isPending) && (
					<ContinuidadeTable
						rows={rows}
						nivel={nivel}
						criterio={criterio}
						resetKey={[
							visao,
							periodo?.inicio ?? "",
							periodo?.fim ?? "",
							criterio,
							municipio ?? "",
							bairro ?? "",
						].join("|")}
						loading={carregando}
						refreshing={atualizando}
						error={erroTabela}
						onRetry={() => void ativa.refetch()}
						onOpen={abrirLinha}
					/>
				)}
			</section>

			<AlimentadorSheet
				alimentador={alimentador}
				periodo={periodo}
				criterio={metrica}
				fromRecorte={Boolean(bairro)}
				linhas={serie.data}
				loading={serie.isLoading}
				refreshing={serie.isFetching && !serie.isLoading}
				error={
					serie.isError
						? "Não foi possível carregar o histórico do alimentador."
						: null
				}
				onRetry={() => void serie.refetch()}
				onCriterioChange={trocarSerie}
				onClose={fecharPainel}
			/>
		</Pagina>
	);
}
