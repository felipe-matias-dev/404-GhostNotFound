import {
	getRouteApi,
	Link,
	useLocation,
	useRouterState,
} from "@tanstack/react-router";
import { useEffect, useMemo, useRef } from "react";
import { HeaderTrilha } from "#/components/layout/header";
import { Pagina } from "#/components/layout/pagina";
import {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbLink,
	BreadcrumbList,
	BreadcrumbPage,
	BreadcrumbSeparator,
} from "#/components/ui/breadcrumb";
import {
	SegmentedControl,
	type SegmentedOption,
} from "#/components/ui/segmented-control";
import { CLASSE_ROTULO, useFiltrosPortal } from "#/features/filtros";
import { useIndicadoresMensais } from "#/features/indicadores";
import type { ParPeriodos } from "#/lib/filtros";
import { AlimentadorSheet } from "../components/alimentador-sheet";
import { ContinuidadeTable } from "../components/continuidade-table";
import { IndicadoresRede } from "../components/indicadores-rede";
import { linhasDoRanking } from "../conversions";
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

const CRITERIOS: readonly SegmentedOption<Criterio>[] = [
	{ value: "dec", label: "DEC" },
	{ value: "fec", label: "FEC" },
];

const SEM_PERIODO = "Escolha um período para consultar a continuidade.";

const RECORTE_GLOBAL = "Limpe o recorte para consultar todos os alimentadores";

export function RedePage() {
	const search = route.useSearch();
	const navigate = route.useNavigate();

	// O período da Rede é o compartilhado: a URL traduz o mesmo trecho para `inicio`/`fim`.
	const { filtros } = useFiltrosPortal();
	// A URL bruta ainda pode trazer campos que o schema já descartou (bairro órfão, mês
	// inválido, a antiga `serie`): comparar só com o search validado esconderia esses casos.
	const buscaBruta = useLocation({
		select: (local) => local.search,
	}) as Record<string, unknown>;
	const par = filtros.periodo_atual;
	const periodo = useMemo<Periodo | undefined>(() => {
		if (!par) return undefined;
		const [inicio, fim] = par.split("/");
		return inicio && fim ? { inicio, fim } : undefined;
	}, [par]);

	const criterio: Criterio = search.criterio ?? "dec";
	const alimentador = search.alimentador;
	const municipio = filtros.municipio;
	const bairro = filtros.bairro;
	const classe = filtros.classe;
	const recorte = useMemo(
		() => ({ municipio, bairro, classe }),
		[municipio, bairro, classe],
	);
	// Com recorte, o ranking global não se aplica; a preferência explícita volta sem recorte.
	const comRecorte = Boolean(municipio || bairro || classe);
	const visaoSalva: VisaoRede =
		buscaBruta.visao === "localidades" ? "localidades" : "alimentadores";
	const visao: VisaoRede = comRecorte ? "localidades" : visaoSalva;

	const visoes = useMemo<readonly SegmentedOption<VisaoRede>[]>(
		() => [
			{ value: "alimentadores", label: "Alimentadores", disabled: comRecorte },
			{ value: "localidades", label: "Localidades" },
		],
		[comRecorte],
	);

	// Hooks em ordem fixa; a consulta da visão inativa fica desligada por skipToken.
	const ranking = useRankingContinuidade(
		periodo,
		criterio,
		visao === "alimentadores" && !comRecorte,
	);
	const recortes = useRecortesContinuidade(
		periodo,
		criterio,
		recorte,
		visao === "localidades",
	);
	const serie = useSerieAlimentador(periodo, alimentador);
	// A referência do painel é a empresa inteira, como o histórico do alimentador, que também
	// ignora o recorte; só é pedida com o painel aberto.
	const parEmpresa: ParPeriodos | undefined =
		alimentador && filtros.periodo_atual && filtros.periodo_base
			? {
					periodo_base: filtros.periodo_base,
					periodo_atual: filtros.periodo_atual,
				}
			: undefined;
	const empresa = useIndicadoresMensais(parEmpresa, {});

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

	const localidade = bairro
		? `${bairro}, ${municipio}`
		: (municipio ?? "Empresa inteira");
	const tituloIndicadores = classe
		? `${localidade} · ${CLASSE_ROTULO[classe]}`
		: localidade;

	// A forma canônica da tela: período compartilhado, padrões omitidos e campos sem sentido fora.
	const alvo = useMemo<RedeSearch>(
		() => ({
			inicio: periodo?.inicio,
			fim: periodo?.fim,
			periodo_base: filtros.periodo_base,
			criterio: criterio === "dec" ? undefined : criterio,
			visao: visaoSalva === "localidades" ? "localidades" : undefined,
			municipio,
			bairro,
			classe,
			alimentador,
		}),
		[
			periodo?.inicio,
			periodo?.fim,
			filtros.periodo_base,
			criterio,
			visaoSalva,
			municipio,
			bairro,
			classe,
			alimentador,
		],
	);
	const temPeriodo = Boolean(periodo);

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
	// Descer ou subir de nível troca a tabela inteira: o foco vai ao novo título, que anuncia
	// onde o usuário está. Mudanças vindas da barra de filtros não roubam o foco.
	const focarTitulo = useRef(false);

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

	// biome-ignore lint/correctness/useExhaustiveDependencies: o efeito reage à troca de nível.
	useEffect(() => {
		if (!focarTitulo.current) return;
		focarTitulo.current = false;
		tituloRef.current?.focus();
	}, [municipio, bairro]);

	const ir = (proximo: Partial<RedeSearch>, replace = false) =>
		navigate({
			to: "/rede",
			search: { ...alvo, ...proximo },
			replace,
			resetScroll: false,
		});

	// Trocar de visão fecha o painel, mas nunca limpa o recorte compartilhado: com recorte, a
	// opção global está desabilitada.
	const escolherVisao = (proxima: VisaoRede) => {
		if (proxima === "alimentadores" && comRecorte) return;
		void ir({
			visao: proxima === "localidades" ? "localidades" : undefined,
			alimentador: undefined,
		});
	};

	const escolherCriterio = (proximo: Criterio) =>
		void ir({ criterio: proximo === "dec" ? undefined : proximo });

	// Abrir a linha grava o nível que a resposta atual oferece, nunca o da resposta anterior.
	const abrirLinha = (linha: LinhaContinuidade) => {
		const atual =
			visao === "alimentadores" ? "alimentador" : recortes.data?.nivel;
		if (!atual) return;
		const ativo = document.activeElement;
		opener.current =
			ativo instanceof HTMLElement && ativo !== document.body ? ativo : null;
		if (atual === "municipio") {
			focarTitulo.current = true;
			void ir({
				visao: "localidades",
				municipio: linha.segmento,
				bairro: undefined,
				alimentador: undefined,
			});
			return;
		}
		if (atual === "bairro") {
			focarTitulo.current = true;
			void ir({
				visao: "localidades",
				bairro: linha.segmento,
				alimentador: undefined,
			});
			return;
		}
		void ir({ alimentador: linha.segmento });
	};

	// Fechar remove só o alimentador; tabela, recorte, período e página ficam.
	const fecharPainel = () => void ir({ alimentador: undefined });

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

	const carregando = ativa.isLoading;
	const atualizando = ativa.isFetching && !ativa.isLoading;
	const erroTabela = ativa.isError
		? "Não foi possível carregar a continuidade deste recorte."
		: null;

	const legenda =
		n_meses === undefined
			? "Maiores índices primeiro"
			: `Maiores índices primeiro · ${n_meses} ${n_meses === 1 ? "mês" : "meses"} com dados na base`;

	// Subir pela trilha volta ao nível de cima sem perder classe, período nem critério.
	const subir = (proximo: Partial<RedeSearch>) => ({
		...alvo,
		visao: "localidades" as const,
		alimentador: undefined,
		...proximo,
	});

	return (
		<Pagina className="max-w-none">
			{visao === "localidades" && municipio && (
				<HeaderTrilha>
					<Breadcrumb aria-label="Recorte da rede" className="min-w-0">
						<BreadcrumbList>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbLink
									render={
										<Link
											to="/rede"
											search={subir({
												municipio: undefined,
												bairro: undefined,
											})}
											onClick={() => {
												focarTitulo.current = true;
											}}
										/>
									}
								>
									Municípios
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem className="min-w-0">
								{bairro ? (
									<BreadcrumbLink
										render={
											<Link
												to="/rede"
												search={subir({ bairro: undefined })}
												onClick={() => {
													focarTitulo.current = true;
												}}
											/>
										}
									>
										{municipio}
									</BreadcrumbLink>
								) : (
									<BreadcrumbPage className="truncate">
										{municipio}
									</BreadcrumbPage>
								)}
							</BreadcrumbItem>
							{bairro && (
								<>
									<BreadcrumbSeparator />
									<BreadcrumbItem className="min-w-0">
										<BreadcrumbPage className="truncate">
											{bairro}
										</BreadcrumbPage>
									</BreadcrumbItem>
								</>
							)}
						</BreadcrumbList>
					</Breadcrumb>
				</HeaderTrilha>
			)}

			{periodo && par && (
				<IndicadoresRede
					titulo={tituloIndicadores}
					periodoAtual={par}
					periodoBase={filtros.periodo_base}
					recorte={recorte}
				/>
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
							options={visoes}
						/>
						<SegmentedControl
							label="Critério da tabela"
							value={criterio}
							onValueChange={escolherCriterio}
							options={CRITERIOS}
						/>
					</div>
				</div>

				{comRecorte && (
					<p className="text-small text-text-muted">{RECORTE_GLOBAL}</p>
				)}

				{periodo ? (
					<ContinuidadeTable
						rows={rows}
						nivel={nivel}
						criterio={criterio}
						resetKey={[
							visao,
							periodo.inicio,
							periodo.fim,
							criterio,
							municipio ?? "",
							bairro ?? "",
							classe ?? "",
						].join("|")}
						loading={carregando}
						refreshing={atualizando}
						error={erroTabela}
						onRetry={() => void ativa.refetch()}
						onOpen={abrirLinha}
					/>
				) : (
					<p className="text-body text-text-muted">{SEM_PERIODO}</p>
				)}
			</section>

			<AlimentadorSheet
				alimentador={alimentador}
				periodo={periodo}
				fromRecorte={comRecorte}
				linhas={serie.data}
				empresa={empresa.data}
				loading={serie.isLoading}
				refreshing={serie.isFetching && !serie.isLoading}
				failed={serie.isError}
				onRetry={() => void serie.refetch()}
				onClose={fecharPainel}
			/>
		</Pagina>
	);
}
