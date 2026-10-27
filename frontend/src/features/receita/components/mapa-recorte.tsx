import { useRouter } from "@tanstack/react-router";
import {
	RegionMap,
	type RegionMapShape,
	RMR_CONTEXTO,
	RMR_MUNICIPIOS,
	RMR_VIEWBOX,
} from "#/components/ui/region-map";
import { formatBRL, formatPct } from "#/lib/format";
import {
	chaveNome,
	EFEITO_CAMPO,
	EFEITO_ROTULO,
	type Efeito,
	intensidade,
	legendaDoMapa,
	sobreABase,
} from "../conversions";
import { useBairrosRmr } from "../hooks/use-bairros-rmr";
import { useDecomposicao } from "../hooks/use-decomposicao";
import type { DecomposicaoLinha, ParPeriodos, Recorte } from "../types";

function indexar(linhas: DecomposicaoLinha[] | undefined) {
	const porNome = new Map<string, DecomposicaoLinha>();
	for (const linha of linhas ?? [])
		porNome.set(chaveNome(linha.segmento), linha);
	return porNome;
}

/** Só é clicável o que tem linha na Gold; o nome da Gold vai para a URL. */
export function MapaRecorte({
	par,
	recorte,
	efeito,
	destaque = null,
	onChange,
	className,
}: {
	par: ParPeriodos | undefined;
	recorte: Recorte;
	/** Causa escolhida na ponte: a cor do mapa passa a ser ela, e não a variação total. */
	efeito: Efeito;
	destaque?: DecomposicaoLinha | null;
	onChange: (proximo: Recorte) => void;
	className?: string;
}) {
	const router = useRouter();
	const municipios = useDecomposicao(par, { classe: recorte.classe });
	const bairros = useDecomposicao(
		par,
		{ municipio: recorte.municipio, classe: recorte.classe },
		Boolean(recorte.municipio),
	);
	const geoBairros = useBairrosRmr(Boolean(recorte.municipio));

	const linhasMunicipio = indexar(municipios.data);
	// Enquanto os bairros do novo município não chegam, os do anterior não valem. Sem
	// município, a chave da consulta é a mesma dos municípios e `data` traz as linhas deles.
	const linhasBairro = indexar(
		recorte.municipio && !bairros.isPlaceholderData ? bairros.data : undefined,
	);

	const municipio = recorte.municipio
		? RMR_MUNICIPIOS.find(
				(m) => chaveNome(m.nome) === chaveNome(recorte.municipio ?? ""),
			)
		: undefined;
	const formasBairro = municipio ? (geoBairros.data?.[municipio.id] ?? []) : [];
	const idsBairro = new Set(formasBairro.map((b) => b.id));
	const bairro = recorte.bairro
		? formasBairro.find(
				(b) => chaveNome(b.nome) === chaveNome(recorte.bairro ?? ""),
			)
		: undefined;

	const linhaDe = (forma: RegionMapShape) =>
		(idsBairro.has(forma.id) ? linhasBairro : linhasMunicipio).get(
			chaveNome(forma.nome),
		);

	const recorteDe = (forma: RegionMapShape): Recorte => {
		const nome = linhaDe(forma)?.segmento ?? forma.nome;
		return idsBairro.has(forma.id)
			? { municipio: recorte.municipio, bairro: nome }
			: { municipio: nome };
	};

	const formas = [...RMR_MUNICIPIOS, ...formasBairro];
	const habilitados = new Set(
		formas.filter((f) => linhaDe(f)).map((f) => f.id),
	);

	// Foco: o bairro escolhido; sem ele, os bairros do município (ou o município, se não
	// tem malha de bairros). O resto do mapa fica apagado, como contexto.
	const foco = bairro
		? new Set([bairro.id])
		: municipio
			? new Set(
					formasBairro.length > 0
						? [...idsBairro, municipio.id]
						: [municipio.id],
				)
			: undefined;

	// Classe não tem região no mapa.
	const formasDoDestaque =
		destaque?.nivel === "municipio"
			? RMR_MUNICIPIOS
			: destaque?.nivel === "bairro"
				? formasBairro
				: [];
	const destacada = destaque
		? formasDoDestaque.find(
				(f) => chaveNome(f.nome) === chaveNome(destaque.segmento),
			)
		: undefined;

	return (
		<RegionMap
			label="Mapa da Região Metropolitana do Recife"
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
			highlightId={destacada?.id ?? null}
			selectedId={bairro?.id ?? municipio?.id ?? null}
			getHref={(f) =>
				router.buildLocation({ to: "/receita", search: recorteDe(f) }).href
			}
			onSelect={(f) => onChange(recorteDe(f))}
			onClear={() =>
				onChange(recorte.bairro ? { municipio: recorte.municipio } : {})
			}
			clearLabel={
				recorte.bairro
					? `Todo o município de ${recorte.municipio}`
					: "Todos os municípios"
			}
			getIntensity={(f) => {
				const linha = linhaDe(f);
				return linha ? intensidade(linha, efeito) : 0;
			}}
			legend={legendaDoMapa(efeito)}
			describe={(f) => {
				const linha = linhaDe(f);
				if (!linha) return null;
				const pct = sobreABase(linha, efeito);
				return `${EFEITO_ROTULO[efeito]}: ${formatBRL(linha[EFEITO_CAMPO[efeito]])}${
					pct === null ? "" : ` (${formatPct(pct, { sinal: true })})`
				}`;
			}}
			className={className}
		/>
	);
}
