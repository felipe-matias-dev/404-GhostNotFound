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

/** Mês como número contínuo (ano × 12 + mês - 1), para comparar e somar meses. */
export type Trecho = { inicio: number; fim: number };

const mesDe = (competencia: string) => {
	const [ano, mes] = competencia.split("-").map(Number);
	return ano * 12 + mes - 1;
};

export const competenciaDe = (mes: number) =>
	`${Math.floor(mes / 12)}-${String((mes % 12) + 1).padStart(2, "0")}`;

/** "2025-01/2025-12" → { inicio, fim } em meses contínuos. */
export function trechoDe(periodo: string): Trecho {
	const [inicio, fim] = periodo.split("/");
	return { inicio: mesDe(inicio), fim: mesDe(fim) };
}

export function periodoDe(a: number, b: number): string {
	return `${competenciaDe(Math.min(a, b))}/${competenciaDe(Math.max(a, b))}`;
}

const meses = (periodo: string) => {
	const { inicio, fim } = trechoDe(periodo);
	return fim - inicio + 1;
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

/** Bases gravadas para um período atual, da mais recente para a mais antiga. */
export function basesDoAtual(pares: ParPeriodos[], atual: string): string[] {
	return pares
		.filter((p) => p.periodo_atual === atual)
		.map((p) => p.periodo_base)
		.sort()
		.reverse();
}

/**
 * Par para um período atual escolhido no seletor: a base pedida, se a Gold a gravou; senão o
 * mesmo trecho um ano antes; senão a base mais recente.
 */
export function parDoAtual(
	pares: ParPeriodos[],
	atual: string,
	base?: string,
): ParPeriodos | undefined {
	const bases = basesDoAtual(pares, atual);
	const { inicio, fim } = trechoDe(atual);
	const anoAntes = periodoDe(inicio - 12, fim - 12);
	const escolhida =
		(base && bases.includes(base) && base) ||
		(bases.includes(anoAntes) ? anoAntes : bases[0]);
	return escolhida
		? { periodo_base: escolhida, periodo_atual: atual }
		: undefined;
}

export type Atalho = { rotulo: string; atual: string };

/**
 * Atalhos do seletor, contados a partir do último mês gravado. Só entram os que a Gold
 * gravou, sem repetir o mesmo período com outro nome.
 */
export function atalhos(pares: ParPeriodos[]): Atalho[] {
	const atuais = new Set(pares.map((p) => p.periodo_atual));
	if (!atuais.size) return [];
	const ultimo = Math.max(...[...atuais].map((p) => trechoDe(p).fim));
	const janeiro = ultimo - (ultimo % 12);
	const candidatos: Atalho[] = [
		{ rotulo: "Últimos 12 meses", atual: periodoDe(ultimo - 11, ultimo) },
		{ rotulo: "Ano até o último mês", atual: periodoDe(janeiro, ultimo) },
		{ rotulo: "Último trimestre", atual: periodoDe(ultimo - 2, ultimo) },
		{ rotulo: "Último mês", atual: periodoDe(ultimo, ultimo) },
		{ rotulo: "Ano anterior", atual: periodoDe(janeiro - 12, janeiro - 1) },
	];
	const vistos = new Set<string>();
	return candidatos.filter((a) => {
		if (!atuais.has(a.atual) || vistos.has(a.atual)) return false;
		vistos.add(a.atual);
		return true;
	});
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
