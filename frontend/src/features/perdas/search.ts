import type { SortState } from "#/components/ui/data-table";
import { filtrosCompartilhadosShape, type Recorte } from "#/lib/filtros";
import { z } from "zod";
import {
	ORDENACAO_FILA,
	STATUS_ORDEM,
	type FiltrosFila,
	type OrdenacaoFila,
} from "./types";

const inteiro = (minimo: number, maximo = Number.MAX_SAFE_INTEGER) =>
	z.coerce
		.number()
		.int()
		.min(minimo)
		.max(maximo)
		.optional()
		.catch(undefined);

// A URL traz "true"/"false" como texto; `z.coerce.boolean()` trataria qualquer texto como
// verdadeiro e perderia o desligamento explícito do filtro.
const booleano = z
	.union([z.boolean(), z.literal("true"), z.literal("false")])
	.transform((valor) => valor === true || valor === "true")
	.optional()
	.catch(undefined);

const statusSchema = z.enum(STATUS_ORDEM).optional().catch(undefined);
const secaoSchema = z.enum(["fila", "ordens"]).optional().catch(undefined);
const ordenarPorSchema = z.enum(ORDENACAO_FILA).optional().catch(undefined);
const direcaoSchema = z.enum(["asc", "desc"]).optional().catch(undefined);

export const perdasSearchSchema = z.object({
	...filtrosCompartilhadosShape,
	status: statusSchema,
	secao: secaoSchema,
	queda_min: inteiro(0, 100),
	queda_max: inteiro(0, 100),
	medidor_eletromecanico: booleano,
	leituras_estimadas_min: inteiro(25, 100),
	leituras_estimadas_max: inteiro(25, 100),
	pagina: inteiro(1),
	ordenar_por: ordenarPorSchema,
	direcao: direcaoSchema,
});

export type PerdasSearch = z.infer<typeof perdasSearchSchema>;

export function paginaDaBusca(search: PerdasSearch): number {
	return search.pagina ?? 1;
}

/**
 * Recorte efetivo para a API. Bairro sem município não é enviado (o backend responde 422) e
 * município sem bairro continua valendo.
 */
export function recorteDaBusca(search: PerdasSearch): Recorte {
	return {
		...(search.municipio ? { municipio: search.municipio } : {}),
		...(search.municipio && search.bairro ? { bairro: search.bairro } : {}),
		...(search.classe ? { classe: search.classe } : {}),
	};
}

function faixa(
	minimo: number | undefined,
	maximo: number | undefined,
	piso: number,
): [number, number] | null {
	if (minimo === undefined && maximo === undefined) return null;
	if (minimo === undefined) return [piso, maximo ?? 100];
	if (maximo === undefined) return [minimo, 100];
	return minimo > maximo ? null : [minimo, maximo];
}

export function filtrosDaBusca(search: PerdasSearch): FiltrosFila {
	return {
		queda: faixa(search.queda_min, search.queda_max, 0),
		medidorEletromecanico: search.medidor_eletromecanico ?? false,
		leiturasEstimadas: faixa(
			search.leituras_estimadas_min,
			search.leituras_estimadas_max,
			25,
		),
	};
}

/** Campos exclusivos de Perdas, na ordem dos avisos; cada schema decide o que é valor válido. */
const camposLocais: {
	campo: keyof PerdasSearch;
	rotulo: string;
	schema: z.ZodType<unknown>;
}[] = [
	{ campo: "status", rotulo: "status", schema: statusSchema },
	{ campo: "secao", rotulo: "seção", schema: secaoSchema },
	{ campo: "queda_min", rotulo: "queda", schema: inteiro(0, 100) },
	{ campo: "queda_max", rotulo: "queda", schema: inteiro(0, 100) },
	{
		campo: "medidor_eletromecanico",
		rotulo: "medidor eletromecânico",
		schema: booleano,
	},
	{
		campo: "leituras_estimadas_min",
		rotulo: "leituras estimadas",
		schema: inteiro(25, 100),
	},
	{
		campo: "leituras_estimadas_max",
		rotulo: "leituras estimadas",
		schema: inteiro(25, 100),
	},
	{ campo: "pagina", rotulo: "página", schema: inteiro(1) },
	{ campo: "ordenar_por", rotulo: "ordenação", schema: ordenarPorSchema },
	{ campo: "direcao", rotulo: "ordenação", schema: direcaoSchema },
];

/** Forma canônica dos campos locais: defaults omitidos, pontas isoladas completadas e faixas invertidas descartadas. */
export function buscaCanonicaLocal(
	search: PerdasSearch,
): Partial<PerdasSearch> {
	const filtros = filtrosDaBusca(search);
	const ordenacao = patchDaOrdenacao(sortDaBusca(search));
	return {
		status: search.status,
		secao: search.secao,
		queda_min: filtros.queda?.[0],
		queda_max: filtros.queda?.[1],
		medidor_eletromecanico: filtros.medidorEletromecanico ? true : undefined,
		leituras_estimadas_min: filtros.leiturasEstimadas?.[0],
		leituras_estimadas_max: filtros.leiturasEstimadas?.[1],
		pagina:
			search.pagina !== undefined && search.pagina > 1
				? search.pagina
				: undefined,
		ordenar_por: ordenacao.ordenar_por,
		direcao: ordenacao.direcao,
	};
}

export type NormalizacaoLocal = {
	canonico: Partial<PerdasSearch>;
	avisos: string[];
	altera: boolean;
};

/**
 * Compara a URL bruta com a forma canônica dos campos locais. Campos inválidos e faixas
 * invertidas nunca chegam à API (o schema já os descarta) e são avisados; a URL é reescrita
 * sem eles. Defaults e campos redundantes são omitidos em silêncio.
 */
export function normalizacaoLocal(
	buscaBruta: Record<string, unknown>,
	search: PerdasSearch,
): NormalizacaoLocal {
	const canonico = buscaCanonicaLocal(search);
	const avisos: string[] = [];
	const invalidos = new Set<string>();
	const quedaInvertida =
		search.queda_min !== undefined &&
		search.queda_max !== undefined &&
		search.queda_min > search.queda_max;
	const leiturasInvertidas =
		search.leituras_estimadas_min !== undefined &&
		search.leituras_estimadas_max !== undefined &&
		search.leituras_estimadas_min > search.leituras_estimadas_max;
	let altera = false;

	if (quedaInvertida) {
		avisos.push(
			"Faixa de queda invertida ignorada: a mínima não pode passar da máxima.",
		);
	}
	if (leiturasInvertidas) {
		avisos.push(
			"Faixa de leituras estimadas invertida ignorada: a mínima não pode passar da máxima.",
		);
	}

	for (const { campo, rotulo, schema } of camposLocais) {
		const bruto = buscaBruta[campo];
		if (bruto === undefined) continue;
		const lido = schema.safeParse(bruto);
		const esperado = canonico[campo];
		if (!lido.success || lido.data === undefined) {
			invalidos.add(rotulo);
			altera = true;
			continue;
		}
		if (esperado === undefined || lido.data !== esperado) altera = true;
	}

	if (invalidos.size > 0) {
		avisos.push(
			`Valores inválidos na URL foram ignorados: ${[...invalidos].join(", ")}.`,
		);
	}

	return { canonico, avisos, altera };
}

export function sortDaBusca(search: PerdasSearch): SortState | null {
	const coluna = ORDENACAO_FILA.find(
		(opcao) => opcao === search.ordenar_por && opcao !== "prioridade",
	);
	return coluna
		? { columnId: coluna, direction: search.direcao ?? "asc" }
		: null;
}

/** Patch de URL dos sinais locais, omitindo defaults e voltando à primeira página. */
export function patchDosFiltros(filtros: FiltrosFila): Partial<PerdasSearch> {
	return {
		queda_min: filtros.queda?.[0],
		queda_max: filtros.queda?.[1],
		medidor_eletromecanico: filtros.medidorEletromecanico
			? true
			: undefined,
		leituras_estimadas_min: filtros.leiturasEstimadas?.[0],
		leituras_estimadas_max: filtros.leiturasEstimadas?.[1],
		pagina: undefined,
	};
}

/** Patch de URL da ordenação; `null` volta à ordem da API (`prioridade` ascendente). */
export function patchDaOrdenacao(sort: SortState | null): Partial<PerdasSearch> {
	const coluna: OrdenacaoFila | undefined = ORDENACAO_FILA.find(
		(opcao) => opcao === sort?.columnId,
	);
	return {
		ordenar_por: coluna === "prioridade" ? undefined : coluna,
		direcao: coluna === "prioridade" || !coluna ? undefined : sort?.direction,
		pagina: undefined,
	};
}

export function patchDaPagina(pagina: number): Partial<PerdasSearch> {
	return { pagina: pagina > 1 ? pagina : undefined };
}
