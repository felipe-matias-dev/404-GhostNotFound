import type { RegionMapProps } from "#/components/ui/region-map";
import { formatPct } from "#/lib/format";
import type { DecomposicaoLinha, ParPeriodos, Recorte } from "./types";

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
	if (linha.nivel === "municipio") return { municipio: linha.segmento };
	if (linha.nivel === "bairro")
		return { municipio: filtro.municipio, bairro: linha.segmento };
	return null;
}

const meses = (periodo: string) => {
	const [inicio, fim] = periodo.split("/");
	const [ai, mi] = inicio.split("-").map(Number);
	const [af, mf] = fim.split("-").map(Number);
	return (af - ai) * 12 + (mf - mi) + 1;
};

/**
 * Par que a tela abre sem escolha na URL: a janela de 12 meses com o período atual mais
 * recente. A lista vem ordenada como texto, e o último item pode ser um par de 1 mês.
 */
export function parPadrao(pares: ParPeriodos[]) {
	const anuais = pares.filter((p) => meses(p.periodo_atual) === 12);
	return (anuais.length ? anuais : pares).reduce<ParPeriodos | undefined>(
		(melhor, p) =>
			!melhor || p.periodo_atual > melhor.periodo_atual ? p : melhor,
		undefined,
	);
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
 * Intensidade do mapa, de -1 a 1: variação da receita sobre a receita base do próprio
 * segmento, para um bairro pequeno e um município grande ficarem comparáveis. Só define a
 * cor e o brilho; o número exibido continua sendo a variação em R$ que vem da API.
 */
export function intensidadeVariacao(linha: DecomposicaoLinha): number {
	const { variacao_receita: variacao, receita_base: base } = linha;
	if (base <= 0) return variacao > 0 ? 1 : 0;
	const fracao = variacao / base;
	if (Math.abs(fracao) < ESTAVEL) return 0;
	return Math.max(-1, Math.min(1, fracao / SATURA));
}

export const LEGENDA_VARIACAO: NonNullable<RegionMapProps["legend"]> = {
	title: "Variação da receita",
	ticks: [formatPct(-SATURA), formatPct(0), formatPct(SATURA)],
	description: `vermelho para queda, verde para alta; a cor fica mais forte e brilha mais até ${formatPct(SATURA)} de variação sobre a receita base`,
};
