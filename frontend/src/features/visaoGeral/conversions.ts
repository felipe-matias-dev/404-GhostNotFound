import type {
	ComparacaoIndicadores,
	Indicador,
	IndicadoresPeriodo,
	KpisMensais,
	ParPeriodos,
} from "./types";

export const INDICADORES = [
	"receita_faturada",
	"kwh_faturado",
	"dec",
	"fec",
	"n_chamados",
	"satisfacao_media",
] as const satisfies readonly Indicador[];

/** "2025-03" → "2025-03/2025-03": um mês no formato de período da URL e da API. */
export const periodoDoMes = (competencia: string) =>
	`${competencia}/${competencia}`;

/** Período de um mês só → a competência; `undefined` num trecho de vários meses. */
export function mesDoPeriodo(periodo: string | undefined): string | undefined {
	const [inicio, fim] = periodo?.split("/") ?? [];
	return inicio && inicio === fim ? inicio : undefined;
}

const deslocar = (competencia: string, meses: number) => {
	const [ano, mes] = competencia.split("-").map(Number);
	const total = ano * 12 + (mes - 1) + meses;
	return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, "0")}`;
};

/**
 * Base contra a qual o mês atual é comparado: o mesmo mês do ano anterior, que tira a
 * sazonalidade (padrão), ou o mês anterior.
 */
export type Relacao = "ano" | "mes";

const baseDe = (atual: string, relacao: Relacao) =>
	deslocar(atual, relacao === "ano" ? -12 : -1);

export type Base = { relacao: Relacao; competencia: string };

/** Bases que existem na série para um mês atual, na ordem de preferência. */
export function basesDoMes(competencias: string[], atual: string): Base[] {
	const existentes = new Set(competencias);
	return (["ano", "mes"] as const)
		.map((relacao) => ({ relacao, competencia: baseDe(atual, relacao) }))
		.filter((base) => existentes.has(base.competencia));
}

/** Par de um mês atual, com a relação pedida se ela existir; senão a outra. */
export function parDoMes(
	competencias: string[],
	atual: string,
	relacao: Relacao = "ano",
): ParPeriodos | undefined {
	const bases = basesDoMes(competencias, atual);
	const base =
		bases.find((candidata) => candidata.relacao === relacao) ?? bases[0];
	if (!base) return undefined;
	return {
		periodo_base: periodoDoMes(base.competencia),
		periodo_atual: periodoDoMes(atual),
	};
}

/** Como a base do par se relaciona com o mês atual; `undefined` se não for nenhuma das duas. */
export function relacaoDoPar(par: ParPeriodos): Relacao | undefined {
	const atual = mesDoPeriodo(par.periodo_atual);
	const base = mesDoPeriodo(par.periodo_base);
	if (!atual || !base) return undefined;
	if (base === baseDe(atual, "ano")) return "ano";
	if (base === baseDe(atual, "mes")) return "mes";
	return undefined;
}

/**
 * Par que a tela abre sem escolha na URL: o mês mais recente contra o mesmo mês do ano
 * anterior; sem ele, o mês anterior. A série vem em ordem, do mais antigo ao mais recente.
 */
export function parPadrao(competencias: string[]): ParPeriodos | undefined {
	for (const atual of [...competencias].reverse()) {
		const par = parDoMes(competencias, atual);
		if (par) return par;
	}
	return undefined;
}

/**
 * O par da URL, se é mês contra mês, com os dois meses na série e a base antes do atual;
 * senão o padrão. Trechos de vários meses esperam a rota de comparação do backend (DEC-036).
 */
export function parEscolhido(
	competencias: string[],
	periodoBase: string | undefined,
	periodoAtual: string | undefined,
): ParPeriodos | undefined {
	const base = mesDoPeriodo(periodoBase);
	const atual = mesDoPeriodo(periodoAtual);
	const existentes = new Set(competencias);
	if (
		base &&
		atual &&
		base < atual &&
		existentes.has(base) &&
		existentes.has(atual)
	) {
		return {
			periodo_base: periodoDoMes(base),
			periodo_atual: periodoDoMes(atual),
		};
	}
	return parPadrao(competencias);
}

/** Variação do atual sobre a base, em fração; nula sem um dos lados ou com base zero. */
export function variacao(
	base: number | null,
	atual: number | null,
): number | null {
	if (base == null || atual == null || base === 0) return null;
	return (atual - base) / base;
}

function indicadoresDoMes(
	linhas: KpisMensais[],
	periodo: string,
): IndicadoresPeriodo {
	const linha = linhas.find((l) => l.competencia === mesDoPeriodo(periodo));
	const valores = Object.fromEntries(
		INDICADORES.map((indicador) => [indicador, linha?.[indicador] ?? null]),
	) as Record<Indicador, number | null>;
	return { periodo, valores };
}

/**
 * Comparação mês contra mês a partir da série mensal: os valores são os da Gold, sem conta, e
 * a tela só calcula a variação percentual, como na tela de receita (DEC-035).
 */
export function compararMeses(
	linhas: KpisMensais[],
	par: ParPeriodos,
): ComparacaoIndicadores {
	const base = indicadoresDoMes(linhas, par.periodo_base);
	const atual = indicadoresDoMes(linhas, par.periodo_atual);
	return {
		base,
		atual,
		variacao: Object.fromEntries(
			INDICADORES.map((indicador) => [
				indicador,
				variacao(base.valores[indicador], atual.valores[indicador]),
			]),
		) as Record<Indicador, number | null>,
	};
}
