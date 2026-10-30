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
const periodo = z.string().regex(PERIODO)
	.refine((value) => value.slice(0, 7) <= value.slice(8)).optional().catch(undefined);

// Preserva períodos inválidos até o portal avisar e normalizar a URL, antes das consultas.
export const filtrosCompartilhadosShape = {
	municipio: texto,
	bairro: texto,
	classe: z.enum(CLASSES).optional().catch(undefined),
	periodo_base: z.string().optional().catch(undefined),
	periodo_atual: z.string().optional().catch(undefined),
};

const schema = z.object({ ...filtrosCompartilhadosShape, periodo_base: periodo, periodo_atual: periodo });

/** "2024-03" um ano antes → "2023-03"; sem ano anterior, o mês fica como está. */
export function anoAnterior(competencia: string): string | undefined {
	const ano = Number(competencia.slice(0, 4));
	if (!Number.isFinite(ano) || ano <= 0) return undefined;
	return `${String(ano - 1).padStart(4, "0")}${competencia.slice(4)}`;
}

/**
 * "2025-01/2025-03" um ano antes → "2024-01/2024-03". É a base sugerida quando a URL traz
 * o período atual sem a base gravada.
 */
export function periodoAnterior(periodoAtual: string): string | undefined {
	const [inicio, fim] = periodoAtual.split("/");
	const baseInicio = inicio ? anoAnterior(inicio) : undefined;
	const baseFim = fim ? anoAnterior(fim) : undefined;
	return baseInicio && baseFim ? `${baseInicio}/${baseFim}` : undefined;
}

/** Período atual da busca da tela: `/rede` o escreve como duas pontas, as demais como par. */
function periodoDaBusca(destino: DestinoPortal, search: Record<string, unknown>) {
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
	// Base sem período atual não diz nada; período atual sem base vale o mesmo trecho um ano antes.
	const base = parsed.periodo_atual
		? (parsed.periodo_base ?? periodoAnterior(parsed.periodo_atual))
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
