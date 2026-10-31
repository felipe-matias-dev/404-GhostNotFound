import type { RegionMapProps } from "#/components/ui/region-map";
import type { WaterfallStep } from "#/components/ui/waterfall-chart";
import type { Recorte } from "#/lib/filtros";
import { formatPct } from "#/lib/format";
import type { DecomposicaoLinha } from "./types";

export type Nivel = DecomposicaoLinha["nivel"];

export const NIVEL_ROTULO: Record<Nivel, string> = {
	municipio: "Município",
	bairro: "Bairro",
	classe: "Classe",
};

export function nivelDoFiltro(filtro: Recorte): Nivel {
	if (filtro.bairro) return "classe";
	if (filtro.municipio) return "bairro";
	return "municipio";
}

export function filtroAoAbrir(
	filtro: Recorte,
	linha: DecomposicaoLinha,
): Recorte | null {
	if (linha.nivel === "municipio")
		return { municipio: linha.segmento, bairro: undefined };
	if (linha.nivel === "bairro")
		return { municipio: filtro.municipio, bairro: linha.segmento };
	return null;
}

/**
 * Chave para casar o município ou bairro da Gold com o da malha do IBGE: sem acento, caixa
 * ou espaço sobrando ("Jaboatão dos Guararapes" = "JABOATAO DOS GUARARAPES").
 */
export function chaveNome(nome: string): string {
	return nome
		.normalize("NFD")
		.replace(/\p{Diacritic}/gu, "")
		.toLowerCase()
		.replace(/\s+/g, " ")
		.trim();
}

// Escala do mapa, em fração da receita base: abaixo de 0,5% é estável; 10% ou mais satura.
const ESTAVEL = 0.005;
const SATURA = 0.1;

/**
 * Quanto o efeito pesa sobre a receita base do próprio segmento, para um bairro pequeno e um
 * município grande ficarem comparáveis. `null` sem receita base (segmento novo).
 */
export function sobreABase(
	linha: DecomposicaoLinha,
	efeito: Efeito,
): number | null {
	if (linha.receita_base <= 0) return null;
	return linha[EFEITO_CAMPO[efeito]] / linha.receita_base;
}

/**
 * Intensidade do mapa, de -1 a 1: o efeito escolhido sobre a receita base. Só define a cor e
 * o brilho; o número exibido continua sendo o valor em R$ que vem da API.
 */
export function intensidade(linha: DecomposicaoLinha, efeito: Efeito): number {
	const fracao = sobreABase(linha, efeito);
	if (fracao === null) return Math.sign(linha[EFEITO_CAMPO[efeito]]);
	if (Math.abs(fracao) < ESTAVEL) return 0;
	return Math.max(-1, Math.min(1, fracao / SATURA));
}

export function legendaDoMapa(
	efeito: Efeito,
): NonNullable<RegionMapProps["legend"]> {
	const titulo =
		efeito === "variacao"
			? "Variação da receita"
			: `Efeito ${EFEITO_ROTULO[efeito].toLowerCase()}`;
	return {
		title: titulo,
		ticks: [formatPct(-SATURA), formatPct(0), formatPct(SATURA)],
		description: `${titulo} sobre a receita base de cada região: vermelho para queda, verde para alta; a cor fica mais forte e brilha mais até ${formatPct(SATURA)}`,
	};
}

/** Campos numéricos da linha (receitas, variação e efeitos). */
export type CampoValor = {
	[K in keyof DecomposicaoLinha]: DecomposicaoLinha[K] extends number
		? K
		: never;
}[keyof DecomposicaoLinha];

/**
 * Ponte do recorte na tela: a soma dos segmentos do nível abaixo (os efeitos são somáveis,
 * DEC-023; o frontend só soma o que a Gold calculou, DEC-035). O efeito preço entra aberto em
 * tarifa e bandeira, que somam o `efeito_preco`; somar os três contaria o preço duas vezes.
 * A receita atual sai dos passos: cada linha fecha com a variação só dentro da tolerância do
 * contrato, e somada sobre dezenas de segmentos a sobra desalinharia o último degrau.
 */
export function passosDaPonte(linhas: DecomposicaoLinha[]): WaterfallStep[] {
	if (linhas.length === 0) return [];
	// Em centavos: somar dezenas de valores em ponto flutuante deixa resíduo na última casa.
	const centavos = (valor: number) => Math.round(valor * 100) / 100;
	const soma = (campo: CampoValor) =>
		centavos(linhas.reduce((total, l) => total + l[campo], 0));
	const base = soma("receita_base");
	const efeitos = CAUSAS.map(
		(efeito): WaterfallStep => ({
			id: efeito,
			label: EFEITO_ROTULO[efeito],
			value: soma(EFEITO_CAMPO[efeito]),
			kind: "delta",
		}),
	);
	return [
		{ id: "base", label: "Receita base", value: base, kind: "total" },
		...efeitos,
		{
			id: "atual",
			label: "Receita atual",
			value: centavos(efeitos.reduce((total, p) => total + p.value, base)),
			kind: "total",
		},
	];
}

/**
 * Recorte da ponte que a tela ranqueia e ordena: a variação total ou uma das causas. Na
 * ordem da ponte; o efeito preço entra só aberto em tarifa e bandeira.
 */
export const EFEITOS = [
	"variacao",
	"tarifa",
	"bandeira",
	"volume",
	"mix",
] as const;

export type Efeito = (typeof EFEITOS)[number];

export type Causa = Exclude<Efeito, "variacao">;

export const CAUSAS: Causa[] = ["tarifa", "bandeira", "volume", "mix"];

export const EFEITO_CAMPO: Record<Efeito, CampoValor> = {
	variacao: "variacao_receita",
	tarifa: "efeito_tarifa",
	bandeira: "efeito_bandeira",
	volume: "efeito_volume",
	mix: "efeito_mix",
};

export const EFEITO_ROTULO: Record<Efeito, string> = {
	variacao: "Variação",
	tarifa: "Preço · tarifa",
	bandeira: "Preço · bandeira",
	volume: "Volume",
	mix: "Mix",
};

/** Etapa da ponte → causa; os totais (receita base e atual) não são causa. */
export function causaDoPasso(id: string): Causa | null {
	return (CAUSAS as string[]).includes(id) ? (id as Causa) : null;
}

/** Ranquear pelo valor em R$ ou pelo peso sobre a receita base do segmento. */
export type Medida = "brl" | "pct";

export type Contribuinte = {
	linha: DecomposicaoLinha;
	/** Valor do efeito em R$. */
	valor: number;
	/** Efeito sobre a receita base; `null` sem receita base. */
	pct: number | null;
	/** Tamanho da barra na medida escolhida, sobre o maior da lista, de 0 a 1. */
	fracao: number;
};

export type Ranking = {
	/** `false`: nenhum segmento caiu, e a lista traz as menores altas. */
	houveQueda: boolean;
	/** Quedas e total contam todos os segmentos, inclusive os que ficam fora do ranking em %. */
	quedas: number;
	total: number;
	/** Vazio só em %, quando nenhum segmento da lista tem receita base. */
	itens: Contribuinte[];
};

/**
 * Maiores contribuintes da queda no efeito escolhido, da maior queda para a menor. Só entram
 * segmentos que caíram; se nenhum caiu, a lista mostra quem subiu menos, sem chamar de queda.
 * Em %, segmento sem receita base fica fora da lista (não há base para comparar), mas continua
 * contando como queda.
 */
export function rankingDaQueda(
	linhas: DecomposicaoLinha[],
	efeito: Efeito,
	medida: Medida = "brl",
	limite = 5,
): Ranking {
	const campo = EFEITO_CAMPO[efeito];
	const quedas = linhas.filter((linha) => linha[campo] < 0).length;
	const ordenados = linhas
		.map((linha) => {
			const pct = sobreABase(linha, efeito);
			const chave = medida === "pct" ? pct : linha[campo];
			return { linha, valor: linha[campo], pct, chave };
		})
		.filter((c): c is typeof c & { chave: number } => c.chave !== null)
		.filter((c) => !quedas || c.valor < 0)
		.sort(
			(a, b) =>
				a.chave - b.chave || a.linha.segmento.localeCompare(b.linha.segmento),
		);
	const escolhidos = ordenados.slice(0, limite);
	const maior = Math.max(0, ...escolhidos.map((c) => Math.abs(c.chave)));
	return {
		houveQueda: quedas > 0,
		quedas,
		total: linhas.length,
		itens: escolhidos.map(({ chave, ...c }) => ({
			...c,
			fracao: maior ? Math.abs(chave) / maior : 0,
		})),
	};
}
