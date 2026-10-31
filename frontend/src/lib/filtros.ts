import { z } from "zod";

export const CLASSES = ["B1", "B2", "B3", "A4"] as const;
export type Classe = (typeof CLASSES)[number];
export type Recorte = { municipio?: string; bairro?: string; classe?: Classe };
export type ParPeriodos = { periodo_base: string; periodo_atual: string };
export type FiltrosCompartilhados = {
	municipio?: string;
	bairro?: string;
	classe?: Classe;
	periodo_base?: string;
	periodo_atual?: string;
};
export type DestinoPortal = "/" | "/receita" | "/rede" | "/perdas" | "/uc";

/** Campos que acompanham o usuário entre telas; todos os outros são locais de cada tela. */
export const CAMPOS_COMPARTILHADOS = [
	"municipio",
	"bairro",
	"classe",
	"periodo_base",
	"periodo_atual",
] as const;

const MES = "(?:0[1-9]|1[0-2])";
const PERIODO = new RegExp(`^\\d{4}-${MES}/\\d{4}-${MES}$`);
const MES_SOZINHO = new RegExp(`^\\d{4}-${MES}$`);

const texto = z.string().trim().min(1).optional().catch(undefined);
const periodo = z
	.string()
	.regex(PERIODO)
	.refine((value) => value.slice(0, 7) <= value.slice(8))
	.optional()
	.catch(undefined);

// Preserva períodos inválidos até o portal avisar e normalizar a URL, antes das consultas.
export const filtrosCompartilhadosShape = {
	municipio: texto,
	bairro: texto,
	classe: z.enum(CLASSES).optional().catch(undefined),
	periodo_base: z.string().optional().catch(undefined),
	periodo_atual: z.string().optional().catch(undefined),
};

const schema = z.object({
	...filtrosCompartilhadosShape,
	periodo_base: periodo,
	periodo_atual: periodo,
});

/** Base de mesma duração, um ano antes ou imediatamente antes de uma janela maior. */
export function periodoAnterior(periodoAtual: string): string | undefined {
	if (!PERIODO.test(periodoAtual)) return undefined;
	const [inicio, fim] = periodoAtual.split("/");
	if (inicio > fim) return undefined;
	const numero = (mes: string) =>
		Number(mes.slice(0, 4)) * 12 + Number(mes.slice(5)) - 1;
	const primeiro = numero(inicio);
	const ultimo = numero(fim);
	const deslocamento = Math.max(12, ultimo - primeiro + 1);
	if (primeiro < deslocamento) return undefined;
	const competencia = (mes: number) =>
		`${String(Math.floor(mes / 12)).padStart(4, "0")}-${String((mes % 12) + 1).padStart(2, "0")}`;
	return `${competencia(primeiro - deslocamento)}/${competencia(ultimo - deslocamento)}`;
}

export function periodosOrdenados(base: string, atual: string): boolean {
	return (
		PERIODO.test(base) &&
		PERIODO.test(atual) &&
		base.slice(0, 7) <= base.slice(8) &&
		atual.slice(0, 7) <= atual.slice(8) &&
		base.slice(8) < atual.slice(0, 7)
	);
}

/** Período atual da busca da tela: `/rede` o escreve como duas pontas, as demais como par. */
function periodoDaBusca(
	destino: DestinoPortal,
	search: Record<string, unknown>,
) {
	if (destino !== "/rede") return search.periodo_atual;
	const { inicio, fim } = search;
	if (typeof inicio !== "string" || typeof fim !== "string") return undefined;
	if (!MES_SOZINHO.test(inicio) || !MES_SOZINHO.test(fim) || inicio > fim) {
		return undefined;
	}
	return `${inicio}/${fim}`;
}

export function lerFiltrosCompartilhados(
	destino: DestinoPortal,
	search: Record<string, unknown>,
): FiltrosCompartilhados {
	const parsed = schema.parse({
		...search,
		periodo_atual: periodoDaBusca(destino, search),
	});
	const base = parsed.periodo_atual
		? parsed.periodo_base &&
			periodosOrdenados(parsed.periodo_base, parsed.periodo_atual)
			? parsed.periodo_base
			: periodoAnterior(parsed.periodo_atual)
		: undefined;
	return {
		municipio: parsed.municipio,
		bairro: parsed.municipio ? parsed.bairro : undefined,
		classe: parsed.classe,
		periodo_base: base,
		periodo_atual: parsed.periodo_atual,
	};
}

export function gravarFiltrosCompartilhados(
	destino: DestinoPortal,
	filtros: FiltrosCompartilhados,
): Record<string, string | undefined> {
	const normalizados = lerFiltrosCompartilhados("/", filtros);
	if (destino === "/rede") {
		const [inicio, fim] = normalizados.periodo_atual?.split("/") ?? [];
		return {
			municipio: normalizados.municipio,
			bairro: normalizados.bairro,
			classe: normalizados.classe,
			periodo_base: normalizados.periodo_base,
			inicio,
			fim,
		};
	}
	return {
		municipio: normalizados.municipio,
		bairro: normalizados.bairro,
		classe: normalizados.classe,
		periodo_base: normalizados.periodo_base,
		periodo_atual: normalizados.periodo_atual,
	};
}

/**
 * Aplica um patch da URL aos filtros compartilhados. Trocar ou remover o município limpa o
 * bairro na mesma navegação, a menos que o patch diga o bairro explicitamente.
 */
export function aplicarPatch(
	filtros: FiltrosCompartilhados,
	patch: Record<string, unknown>,
): FiltrosCompartilhados {
	const proximo: Record<string, unknown> = {
		municipio: filtros.municipio,
		bairro: filtros.bairro,
		classe: filtros.classe,
		periodo_base: filtros.periodo_base,
		periodo_atual: filtros.periodo_atual,
	};
	for (const campo of CAMPOS_COMPARTILHADOS) {
		if (campo in patch) proximo[campo] = patch[campo];
	}
	if (
		"municipio" in patch &&
		patch.municipio !== filtros.municipio &&
		!("bairro" in patch)
	) {
		proximo.bairro = undefined;
	}
	return lerFiltrosCompartilhados("/", proximo);
}

/**
 * O período da URL é soberano. O padrão da tela só entra na URL quando não há período atual
 * e o catálogo ofereceu um par; sem catálogo e sem meses, o período continua ausente.
 */
export function aplicarPeriodoPadrao(
	filtros: FiltrosCompartilhados,
	padrao: ParPeriodos | undefined,
): FiltrosCompartilhados {
	const comPeriodo: FiltrosCompartilhados =
		filtros.periodo_atual || !padrao
			? filtros
			: {
					municipio: filtros.municipio,
					bairro: filtros.bairro,
					classe: filtros.classe,
					periodo_base: padrao.periodo_base,
					periodo_atual: padrao.periodo_atual,
				};
	return lerFiltrosCompartilhados("/", comPeriodo);
}
