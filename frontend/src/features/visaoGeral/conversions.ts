import type { TrendCategory, TrendSeries } from "#/components/ui/trend-chart";
import type { WaterfallStep } from "#/components/ui/waterfall-chart";
import { formatCompetencia, formatCompetenciaCurta } from "#/lib/format";
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

const JANELA = 12;

const fechaJanela = (inicio: string, fim: string) =>
	deslocar(inicio, JANELA - 1) === fim;

/** Janelas de 12 meses no formato de período da URL e da API: "2024-01/2024-12". */
export type Janelas = { base: string; atual: string };

/**
 * A comparação da pergunta da diretoria: os 12 meses mais recentes contra os 12 primeiros da
 * base. Com menos de 24 meses as janelas se sobreporiam, e com buraco na série uma janela não
 * teria 12 meses: nos dois casos, não há comparação.
 */
export function janelasDaBase(competencias: string[]): Janelas | undefined {
	if (competencias.length < 2 * JANELA) return undefined;
	const [bi, bf] = [competencias[0], competencias[JANELA - 1]];
	const [ai, af] = [competencias.at(-JANELA), competencias.at(-1)];
	if (!bi || !bf || !ai || !af) return undefined;
	if (!fechaJanela(bi, bf) || !fechaJanela(ai, af)) return undefined;
	return { base: `${bi}/${bf}`, atual: `${ai}/${af}` };
}

export type Tesoura = {
	categories: TrendCategory[];
	series: TrendSeries[];
	/** As somas de 12 meses por trás de cada ponto, para o tooltip. */
	somas: { receita: number; kwh: number }[];
};

/**
 * Receita e energia faturadas em 12 meses corridos, como variação sobre a primeira janela (0 = igual).
 * A soma de 12 meses tira a sazonalidade, e a variação põe R$ e kWh na mesma escala: a distância
 * entre as linhas é a pergunta da diretoria. Só soma e divide o que a Gold gravou (DEC-041).
 * Janela com buraco na série fica de fora; com menos de dois pontos, não há tesoura.
 */
export function tesoura(linhas: KpisMensais[]): Tesoura {
	const pontos: { competencia: string; receita: number; kwh: number }[] = [];
	for (let fim = JANELA - 1; fim < linhas.length; fim++) {
		const janela = linhas.slice(fim - JANELA + 1, fim + 1);
		const primeira = janela[0];
		const ultima = janela[JANELA - 1];
		if (!primeira || !ultima) continue;
		if (!fechaJanela(primeira.competencia, ultima.competencia)) continue;
		pontos.push({
			competencia: ultima.competencia,
			receita: janela.reduce((soma, l) => soma + l.receita_faturada, 0),
			kwh: janela.reduce((soma, l) => soma + l.kwh_faturado, 0),
		});
	}
	const base = pontos[0];
	if (!base || pontos.length < 2)
		return { categories: [], series: [], somas: [] };
	return {
		categories: pontos.map((p) => ({
			key: p.competencia,
			label: formatCompetenciaCurta(p.competencia),
			title: `12 meses até ${formatCompetencia(p.competencia)}`,
		})),
		series: [
			{
				id: "receita",
				label: "Receita faturada",
				shortLabel: "receita",
				values: pontos.map((p) =>
					base.receita === 0 ? null : p.receita / base.receita - 1,
				),
				color: 1,
				emphasis: true,
			},
			{
				id: "kwh",
				label: "Energia faturada",
				shortLabel: "energia",
				values: pontos.map((p) =>
					base.kwh === 0 ? null : p.kwh / base.kwh - 1,
				),
				color: 2,
				emphasis: true,
			},
		],
		somas: pontos.map(({ receita, kwh }) => ({ receita, kwh })),
	};
}

// Direção da variação já arredondada a uma casa, como a seta do KpiDelta: 0,04% é estável.
const direcao = (pct: number) => Math.sign(Math.round(pct * 10));

/**
 * A frase do topo da tela, só pela direção e pelo tamanho relativo das duas variações (em %,
 * como vêm da API). Os números ficam nos indicadores logo abaixo, e não se repetem aqui.
 */
export function leitura(
	receitaPct: number | null | undefined,
	kwhPct: number | null | undefined,
): string | null {
	if (receitaPct == null || kwhPct == null) return null;
	const r = direcao(receitaPct);
	const k = direcao(kwhPct);
	const ritmo = direcao(receitaPct - kwhPct);
	if (r > 0) {
		if (k < 0) return "A receita cresceu com menos energia faturada.";
		if (k === 0) return "A receita cresceu com a mesma energia faturada.";
		if (ritmo > 0) return "A receita cresceu mais que a energia faturada.";
		if (ritmo < 0) return "A receita cresceu menos que a energia faturada.";
		return "Receita e energia faturada cresceram no mesmo ritmo.";
	}
	if (r === 0) {
		if (k > 0) return "A receita ficou estável com mais energia faturada.";
		if (k < 0) return "A receita ficou estável com menos energia faturada.";
		return "Receita e energia faturada ficaram estáveis.";
	}
	if (k > 0) return "A receita caiu mesmo com mais energia faturada.";
	if (k === 0) return "A receita caiu com a mesma energia faturada.";
	if (ritmo < 0) return "A receita caiu mais que a energia faturada.";
	if (ritmo > 0) return "A receita caiu menos que a energia faturada.";
	return "Receita e energia faturada caíram no mesmo ritmo.";
}

export type EfeitoDaReceita = {
	id: string;
	rotulo: string;
	pct: number | null;
};

/**
 * Os efeitos da ponte de receita como peso sobre a receita base, como a tela de Receita mostra
 * em % (DEC-035). Em % e não em R$: a ponte é sobre a receita de energia e o resumo, sobre a
 * faturada; o peso de cada efeito é o mesmo nas duas medidas, o valor em reais não.
 */
export function efeitosDaReceita(passos: WaterfallStep[]): EfeitoDaReceita[] {
	const base = passos.find((p) => p.kind === "total")?.value ?? 0;
	return passos
		.filter((p) => p.kind === "delta")
		.map((p) => ({
			id: p.id,
			rotulo: p.label,
			pct: base > 0 ? p.value / base : null,
		}));
}
