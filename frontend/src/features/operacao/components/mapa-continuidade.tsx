import { useRouter } from "@tanstack/react-router";
import { Button } from "#/components/ui/button";
import {
	chaveNome,
	RegionMap,
	type RegionMapShape,
	RMR_CONTEXTO,
	RMR_MUNICIPIOS,
	RMR_VIEWBOX,
	useBairrosRmr,
} from "#/components/ui/region-map";
import { useFiltrosPortal } from "#/features/filtros";
import {
	formatHoras,
	formatIndice,
	formatNumero,
	formatPeriodoCurto,
} from "#/lib/format";
import { useRecortesContinuidade } from "../hooks/use-continuidade";
import type { Criterio, LinhaContinuidade, Periodo, Recorte } from "../types";

const indexar = (linhas: readonly LinhaContinuidade[] | undefined) =>
	new Map(linhas?.map((linha) => [chaveNome(linha.segmento), linha]));

export function MapaContinuidade({
	periodo,
	recorte,
	criterio,
	onChange,
}: {
	periodo: Periodo;
	recorte: Recorte;
	criterio: Criterio;
	onChange: (proximo: Recorte) => void;
}) {
	const router = useRouter();
	const { searchPara } = useFiltrosPortal();
	const municipios = useRecortesContinuidade(
		periodo,
		criterio,
		{ classe: recorte.classe },
		"municipio",
		undefined,
		true,
	);
	const bairros = useRecortesContinuidade(
		periodo,
		criterio,
		{ municipio: recorte.municipio, classe: recorte.classe },
		"bairro",
		undefined,
		Boolean(recorte.municipio),
	);
	const geoBairros = useBairrosRmr(Boolean(recorte.municipio));
	const linhasMunicipio = indexar(municipios.data?.recortes);
	const linhasBairro = indexar(
		recorte.municipio ? bairros.data?.recortes : undefined,
	);
	const municipio = RMR_MUNICIPIOS.find(
		(m) =>
			recorte.municipio && chaveNome(m.nome) === chaveNome(recorte.municipio),
	);
	const formasBairro = municipio ? (geoBairros.data?.[municipio.id] ?? []) : [];
	const idsBairro = new Set(formasBairro.map((b) => b.id));
	const bairro = formasBairro.find(
		(b) => recorte.bairro && chaveNome(b.nome) === chaveNome(recorte.bairro),
	);
	const formas = [...RMR_MUNICIPIOS, ...formasBairro];
	const linhaDe = (forma: RegionMapShape) =>
		(idsBairro.has(forma.id) ? linhasBairro : linhasMunicipio).get(
			chaveNome(forma.nome),
		);
	const habilitados = new Set(
		formas.filter((f) => linhaDe(f)?.[criterio] != null).map((f) => f.id),
	);
	const formasDaEscala =
		formasBairro.length > 0 ? formasBairro : RMR_MUNICIPIOS;
	const temDados = formasDaEscala.some(
		(forma) => linhaDe(forma)?.[criterio] != null,
	);
	const maximo = formasDaEscala.reduce(
		(maior, forma) => Math.max(maior, linhaDe(forma)?.[criterio] ?? 0),
		0,
	);
	const foco = bairro
		? new Set([bairro.id])
		: municipio
			? new Set([municipio.id, ...idsBairro])
			: recorte.municipio
				? new Set<string>()
				: undefined;
	const recorteDe = (forma: RegionMapShape): Recorte =>
		idsBairro.has(forma.id)
			? { municipio: recorte.municipio, bairro: linhaDe(forma)?.segmento }
			: { municipio: linhaDe(forma)?.segmento, bairro: undefined };
	const consulta =
		recorte.municipio && formasBairro.length > 0 ? bairros : municipios;
	const carregando =
		municipios.isLoading ||
		(Boolean(municipio) && (geoBairros.isLoading || bairros.isLoading));
	const falhaMalha = Boolean(municipio) && geoBairros.isError;
	const nomesNaMalha = new Set(formasDaEscala.map((f) => chaveNome(f.nome)));
	const semMalha =
		(formasBairro.length > 0 ? bairros : municipios).data?.recortes.filter(
			(linha) => !nomesNaMalha.has(chaveNome(linha.segmento)),
		).length ?? 0;
	const formatar = criterio === "dec" ? formatHoras : formatIndice;
	const indice = criterio.toUpperCase();
	const unidade = criterio === "dec" ? "h/UC" : "interrupções/UC";
	const periodoRotulo = formatPeriodoCurto(`${periodo.inicio}/${periodo.fim}`);

	return (
		<section
			aria-label="Continuidade no território"
			className="flex min-w-0 flex-col gap-2 lg:sticky lg:top-5 lg:self-start"
		>
			<RegionMap
				label={`Mapa de ${indice} da Região Metropolitana do Recife`}
				viewBox={RMR_VIEWBOX}
				shapes={formas}
				context={RMR_CONTEXTO}
				enabledIds={habilitados}
				containerIds={
					municipio && formasBairro.length > 0
						? new Set([municipio.id])
						: undefined
				}
				focusIds={foco}
				selectedId={bairro?.id ?? municipio?.id ?? null}
				colorScale="sequential"
				getIntensity={(forma) =>
					maximo > 0 ? (linhaDe(forma)?.[criterio] ?? 0) / maximo : 0
				}
				legend={{
					title: `${indice} (${unidade})`,
					ticks: temDados
						? [formatar(0), formatar(maximo / 2), formatar(maximo)]
						: [formatar(null), formatar(null), formatar(null)],
					description: `De zero ao maior ${indice} entre os ${formasBairro.length > 0 ? "bairros do município" : "municípios"} com dados na malha, no período de ${periodoRotulo}. Quanto maior, mais intensa a cor. Não representa limite regulatório.`,
				}}
				getHref={(forma) =>
					router.buildLocation({
						to: "/rede",
						search: searchPara("/rede", recorteDe(forma)) as never,
					}).href
				}
				onSelect={(forma) => onChange(recorteDe(forma))}
				onClear={() =>
					onChange(
						recorte.bairro
							? { bairro: undefined }
							: { municipio: undefined, bairro: undefined },
					)
				}
				clearLabel={
					recorte.bairro
						? `Todo o município de ${recorte.municipio}`
						: "Todos os municípios"
				}
				describe={(forma) => {
					const linha = linhaDe(forma);
					if (!linha || linha[criterio] == null)
						return "Sem dado de continuidade neste período e classe.";
					return `DEC: ${formatHoras(linha.dec)} por UC\nFEC: ${formatIndice(linha.fec)} interrupções por UC\nUCs (média): ${formatNumero(linha.n_uc_medio)}\n${periodoRotulo}`;
				}}
				className="h-96 lg:h-[36rem]"
			/>
			<p className="text-small text-text-muted">
				Maior índice, cor mais intensa. Escala relativa às regiões exibidas, sem
				limite regulatório.
			</p>
			{carregando ? (
				<output className="text-small text-text-muted">
					Carregando continuidade no mapa…
				</output>
			) : consulta.isError || falhaMalha ? (
				<div
					role="alert"
					className="flex flex-wrap items-center gap-2 text-small text-danger"
				>
					<p>
						{falhaMalha
							? "Não foi possível carregar a malha de bairros."
							: "Não foi possível atualizar os dados do mapa."}
					</p>
					<Button
						variant="outline"
						size="xs"
						onClick={() => {
							void consulta.refetch();
							if (falhaMalha) void geoBairros.refetch();
						}}
					>
						Tentar de novo
					</Button>
				</div>
			) : (
				<output className="text-small text-text-muted">
					{recorte.municipio && !municipio
						? "Município fora da malha da RMR. Consulte os dados na tabela."
						: recorte.bairro && !bairro
							? "Bairro sem correspondência na malha. O mapa mantém o contexto do município; consulte o recorte na tabela."
							: !temDados
								? "Sem dados de continuidade nas regiões deste mapa para o período e a classe."
								: semMalha > 0
									? `${semMalha} ${semMalha === 1 ? "região com dados fora" : "regiões com dados fora"} da malha. Consulte a tabela.`
									: consulta.isFetching
										? "Atualizando dados do mapa…"
										: "Selecione uma região para filtrar a Rede."}
				</output>
			)}
		</section>
	);
}
