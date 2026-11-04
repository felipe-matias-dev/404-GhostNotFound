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
import type { components } from "#/lib/api-schema.gen";
import type { Recorte } from "#/lib/filtros";
import { formatKWh, formatNumero } from "#/lib/format";
import { useRecortesFila } from "../hooks/use-recortes-fila";

type RecorteFila = components["schemas"]["RecorteFilaSchema"];

const TAMANHO_RANKING = 10;

const indexar = (linhas: readonly RecorteFila[] | undefined) =>
	new Map(linhas?.map((linha) => [chaveNome(linha.segmento), linha]));

const suspeitas = (total: number) =>
	`${formatNumero(total)} ${total === 1 ? "suspeita" : "suspeitas"}`;

const descricao = (linha: RecorteFila) =>
	`${suspeitas(linha.suspeitas)}\n${formatNumero(linha.suspeitas_sem_ordem_ativa)} sem ordem ativa\n${linha.kwh_recuperavel_est == null ? "Sem estimativa de energia" : `${formatKWh(linha.kwh_recuperavel_est)}/mês a recuperar`}`;

/**
 * Onde estão as suspeitas: o mapa pinta cada município (ou, com um município escolhido, os bairros dele)
 * pela energia estimada a recuperar, e o ranking lista os maiores, inclusive os sem geometria na malha.
 */
export function MapaSuspeitas({
	recorte,
	onChange,
}: {
	recorte: Recorte;
	onChange: (proximo: Recorte) => void;
}) {
	const router = useRouter();
	const { searchPara } = useFiltrosPortal();
	const municipios = useRecortesFila({ classe: recorte.classe }, "municipio");
	const bairros = useRecortesFila(
		{ municipio: recorte.municipio, classe: recorte.classe },
		"bairro",
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
		formas.filter((f) => linhaDe(f)).map((f) => f.id),
	);
	const formasDaEscala =
		formasBairro.length > 0 ? formasBairro : RMR_MUNICIPIOS;
	const temDados = formasDaEscala.some(
		(forma) => linhaDe(forma)?.kwh_recuperavel_est != null,
	);
	const maximo = formasDaEscala.reduce(
		(maior, forma) => Math.max(maior, linhaDe(forma)?.kwh_recuperavel_est ?? 0),
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
			? {
					...recorte,
					municipio: recorte.municipio,
					bairro: linhaDe(forma)?.segmento,
				}
			: { ...recorte, municipio: linhaDe(forma)?.segmento, bairro: undefined };
	const noNivelBairro = Boolean(recorte.municipio);
	const consulta = noNivelBairro ? bairros : municipios;
	const carregando =
		municipios.isLoading ||
		(noNivelBairro && (geoBairros.isLoading || bairros.isLoading));
	const falhaMalha = Boolean(municipio) && geoBairros.isError;
	const ranking = (consulta.data?.recortes ?? []).slice(0, TAMANHO_RANKING);
	const selecionadoNoRanking = (linha: RecorteFila) =>
		noNivelBairro
			? Boolean(recorte.bairro) &&
				chaveNome(linha.segmento) === chaveNome(recorte.bairro ?? "")
			: chaveNome(linha.segmento) === chaveNome(recorte.municipio ?? "");
	const recorteDaLinha = (linha: RecorteFila): Recorte =>
		noNivelBairro
			? {
					...recorte,
					municipio: linha.municipio ?? recorte.municipio,
					bairro: linha.segmento,
				}
			: { ...recorte, municipio: linha.segmento, bairro: undefined };

	return (
		<section
			aria-labelledby="perdas-mapa-titulo"
			className="flex min-w-0 flex-col gap-3 rounded-md border border-border bg-surface-1 p-5 shadow-edge"
		>
			<h2 id="perdas-mapa-titulo" className="text-heading">
				Onde estão as suspeitas
			</h2>
			<div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
				<div className="flex min-w-0 flex-col gap-2">
					{/* Em tela larga, a altura da linha vem do ranking: o mapa, fora do fluxo, ocupa
					    o que sobra, sem que a proporção do SVG estique a linha. */}
					<div className="relative h-80 lg:h-auto lg:min-h-80 lg:flex-1">
						<RegionMap
							label="Mapa de suspeitas da Região Metropolitana do Recife"
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
								maximo > 0
									? (linhaDe(forma)?.kwh_recuperavel_est ?? 0) / maximo
									: 0
							}
							legend={{
								title: "Energia a recuperar (kWh/mês)",
								ticks: temDados
									? [
											formatKWh(0),
											formatKWh(maximo / 2, { compacto: true }),
											formatKWh(maximo, { compacto: true }),
										]
									: [formatKWh(null), formatKWh(null), formatKWh(null)],
								description: `De zero à maior estimativa entre os ${formasBairro.length > 0 ? "bairros do município" : "municípios"} com suspeitas na malha. Quanto maior, mais intensa a cor.`,
							}}
							getHref={(forma) =>
								router.buildLocation({
									to: "/perdas",
									search: searchPara("/perdas", {
										...recorteDe(forma),
										pagina: undefined,
									}) as never,
								}).href
							}
							onSelect={(forma) => onChange(recorteDe(forma))}
							onClear={() =>
								onChange(
									recorte.bairro
										? { ...recorte, bairro: undefined }
										: { ...recorte, municipio: undefined, bairro: undefined },
								)
							}
							clearLabel={
								recorte.bairro
									? `Todo o município de ${recorte.municipio}`
									: "Todos os municípios"
							}
							describe={(forma) => {
								const linha = linhaDe(forma);
								return linha ? descricao(linha) : "Sem suspeitas nesta região.";
							}}
							className="absolute inset-0"
						/>
					</div>
					{carregando ? (
						<output className="text-small text-text-muted">
							Carregando suspeitas no mapa…
						</output>
					) : consulta.isError || falhaMalha ? (
						<div
							role="alert"
							className="flex flex-wrap items-center gap-2 text-small text-danger"
						>
							<p>
								{falhaMalha
									? "Não foi possível carregar a malha de bairros."
									: "Não foi possível carregar as suspeitas por região."}
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
					) : recorte.municipio && !municipio ? (
						<output className="text-small text-text-muted">
							Município fora da malha da RMR. Use a lista ao lado.
						</output>
					) : !temDados ? (
						<output className="text-small text-text-muted">
							Sem estimativa de energia nas regiões deste mapa.
						</output>
					) : null}
				</div>
				<div className="flex min-w-0 flex-col gap-2">
					<h3 className="text-body font-medium text-text">
						Maiores {noNivelBairro ? "bairros" : "municípios"}
					</h3>
					{ranking.length === 0 ? (
						<p className="text-small text-text-muted">
							{consulta.isPending
								? "Carregando…"
								: "Nenhuma suspeita neste recorte."}
						</p>
					) : (
						<ol className="flex flex-col divide-y divide-border">
							{ranking.map((linha, indice) => (
								<li key={`${linha.municipio ?? ""}|${linha.segmento}`}>
									<button
										type="button"
										aria-current={selecionadoNoRanking(linha) || undefined}
										onClick={() => onChange(recorteDaLinha(linha))}
										className="flex w-full items-baseline gap-2 rounded-sm px-1 py-2 text-left outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-focus-ring aria-[current]:bg-surface-2"
									>
										<span className="w-5 shrink-0 text-small text-text-muted tabular-nums">
											{indice + 1}
										</span>
										<span className="flex min-w-0 flex-1 flex-col">
											<span className="truncate text-body text-text">
												{linha.segmento}
											</span>
											<span className="text-small text-text-muted">
												{suspeitas(linha.suspeitas)} ·{" "}
												{formatNumero(linha.suspeitas_sem_ordem_ativa)} sem
												ordem
											</span>
										</span>
										<span className="shrink-0 text-body text-text tabular-nums">
											{linha.kwh_recuperavel_est == null
												? "—"
												: `${formatKWh(linha.kwh_recuperavel_est)}/mês`}
										</span>
									</button>
								</li>
							))}
						</ol>
					)}
				</div>
			</div>
		</section>
	);
}
