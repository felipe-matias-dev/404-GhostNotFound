import {
	getRouteApi,
	Link,
	useLocation,
	useRouterState,
} from "@tanstack/react-router";
import { Fragment, useEffect, useMemo, useRef } from "react";
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
import { AlimentadorSheet } from "../components/alimentador-sheet";
import { ContinuidadeTable } from "../components/continuidade-table";
import { IndicadoresRede } from "../components/indicadores-rede";
import { linhasDoRanking } from "../conversions";
import {
	useContinuidadeMensal,
	useRankingContinuidade,
	useRecortesContinuidade,
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

const VISOES: readonly SegmentedOption<VisaoRede>[] = [
	{ value: "alimentadores", label: "Alimentadores" },
	{ value: "bairros", label: "Bairros" },
	{ value: "localidades", label: "Localidades" },
];

const SEM_PERIODO = "Escolha um período para consultar a continuidade.";

const paraPeriodo = (par: string | undefined): Periodo | undefined => {
	const [inicio, fim] = par?.split("/") ?? [];
	return inicio && fim ? { inicio, fim } : undefined;
};

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
	const periodo = useMemo(() => paraPeriodo(par), [par]);
	// A variação de cada linha é contra a base compartilhada; uma base que não termina antes
	// do período atual não é comparação (a API recusaria), e a coluna some.
	const parBase = filtros.periodo_base;
	const base = useMemo(() => {
		const candidata = paraPeriodo(parBase);
		return candidata && periodo && candidata.fim < periodo.inicio
			? candidata
			: undefined;
	}, [parBase, periodo]);

	const criterio: Criterio = search.criterio ?? "dec";
	const alimentador = search.alimentador;
	const municipio = filtros.municipio;
	const bairro = filtros.bairro;
	const classe = filtros.classe;
	const recorte = useMemo(
		() => ({ municipio, bairro, classe }),
		[municipio, bairro, classe],
	);
	const visao: VisaoRede = search.visao ?? "alimentadores";

	// Hooks em ordem fixa; a consulta da visão inativa fica desligada por skipToken. As três
	// visões respeitam o recorte da barra comum.
	const ranking = useRankingContinuidade(
		periodo,
		criterio,
		recorte,
		base,
		visao === "alimentadores",
	);
	const recortes = useRecortesContinuidade(
		periodo,
		criterio,
		recorte,
		visao === "bairros" ? "bairro" : undefined,
		base,
		visao !== "alimentadores",
	);
	// O painel mostra o alimentador dentro do recorte contra o recorte inteiro (a empresa, sem
	// recorte); as duas séries só são pedidas com ele aberto.
	const serie = useContinuidadeMensal(
		periodo,
		recorte,
		alimentador,
		Boolean(alimentador),
	);
	const referencia = useContinuidadeMensal(
		periodo,
		recorte,
		undefined,
		Boolean(alimentador),
	);

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
			: visao === "bairros"
				? "bairro"
				: (recortes.data?.nivel ?? nivelEsperado);

	const titulo =
		visao === "alimentadores"
			? bairro || municipio
				? `Alimentadores em ${bairro ?? municipio}`
				: "Alimentadores"
			: visao === "bairros"
				? municipio
					? `Bairros de ${municipio}`
					: "Bairros"
				: bairro
					? `Alimentadores em ${bairro}`
					: municipio
						? `Bairros de ${municipio}`
						: "Municípios";

	const geografia = bairro ? `${bairro}, ${municipio}` : municipio;
	const tituloIndicadores = classe
		? `${geografia ?? "Empresa inteira"} · ${CLASSE_ROTULO[classe]}`
		: (geografia ?? "Empresa inteira");
	// O nome do recorte no painel; sem recorte, a referência é a empresa.
	const nomeRecorte =
		[geografia, classe && CLASSE_ROTULO[classe]].filter(Boolean).join(" · ") ||
		undefined;

	// A forma canônica da tela: período compartilhado, padrões omitidos e campos sem sentido fora.
	const alvo = useMemo<RedeSearch>(
		() => ({
			inicio: periodo?.inicio,
			fim: periodo?.fim,
			periodo_base: filtros.periodo_base,
			criterio: criterio === "dec" ? undefined : criterio,
			visao: visao === "alimentadores" ? undefined : visao,
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
			visao,
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

	// Trocar de visão fecha o painel, mas nunca limpa o recorte compartilhado.
	const escolherVisao = (proxima: VisaoRede) =>
		void ir({
			visao: proxima === "alimentadores" ? undefined : proxima,
			alimentador: undefined,
		});

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
		// Um bairro da lista plana leva aos alimentadores dele, com o município no recorte.
		if (visao === "bairros") {
			focarTitulo.current = true;
			void ir({
				visao: undefined,
				municipio: linha.municipio ?? municipio,
				bairro: linha.segmento,
				alimentador: undefined,
			});
			return;
		}
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

	// Subir pela trilha volta ao nível de cima sem perder visão, classe, período nem critério.
	const subir = (proximo: Partial<RedeSearch>) => ({
		...alvo,
		alimentador: undefined,
		...proximo,
	});

	// A trilha do Header: o recorte. Cada nível acima do último é um link que volta à tabela
	// naquele nível.
	const trilha: {
		id: string;
		rotulo: string;
		search: RedeSearch;
	}[] = [];
	if (municipio) {
		trilha.push({
			id: "raiz",
			rotulo: visao === "localidades" ? "Municípios" : "Empresa inteira",
			search: subir({ municipio: undefined, bairro: undefined }),
		});
	}
	if (municipio) {
		trilha.push({
			id: "municipio",
			rotulo: municipio,
			search: subir({ bairro: undefined }),
		});
	}
	if (bairro) trilha.push({ id: "bairro", rotulo: bairro, search: subir({}) });

	return (
		<Pagina className="max-w-none">
			{trilha.length > 0 && (
				<HeaderTrilha>
					<Breadcrumb aria-label="Recorte da rede" className="min-w-0">
						<BreadcrumbList>
							{trilha.map((nivel, indice) => {
								const ultimo = indice === trilha.length - 1;
								return (
									<Fragment key={nivel.id}>
										<BreadcrumbSeparator />
										<BreadcrumbItem className="min-w-0">
											{ultimo ? (
												<BreadcrumbPage className="truncate">
													{nivel.rotulo}
												</BreadcrumbPage>
											) : (
												<BreadcrumbLink
													render={
														<Link
															to="/rede"
															search={nivel.search}
															onClick={() => {
																focarTitulo.current = true;
															}}
														/>
													}
												>
													{nivel.rotulo}
												</BreadcrumbLink>
											)}
										</BreadcrumbItem>
									</Fragment>
								);
							})}
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
							options={VISOES}
						/>
						<SegmentedControl
							label="Critério da tabela"
							value={criterio}
							onValueChange={escolherCriterio}
							options={CRITERIOS}
						/>
					</div>
				</div>

				{periodo ? (
					<ContinuidadeTable
						rows={rows}
						nivel={nivel}
						criterio={criterio}
						periodoBase={base ? parBase : undefined}
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
				aberto={Boolean(alimentador)}
				alimentador={alimentador}
				periodo={periodo}
				recorte={recorte}
				nomeRecorte={nomeRecorte}
				linhas={serie.data}
				referencia={referencia.data}
				loading={serie.isLoading}
				refreshing={serie.isFetching && !serie.isLoading}
				failed={serie.isError}
				onRetry={() => void serie.refetch()}
				onClose={fecharPainel}
			/>
		</Pagina>
	);
}
