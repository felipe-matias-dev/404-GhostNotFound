import {
	type Classe,
	type ParPeriodos,
	periodosOrdenados,
} from "#/lib/filtros";

/** Classes de consumo como no case (`gold_receita_decomposicao.classe`). */
export const CLASSE_ROTULO: Record<Classe, string> = {
	B1: "Residencial",
	B2: "Rural",
	B3: "Comercial e poder público",
	A4: "Industrial MT",
};

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
	const validos = pares.filter((p) =>
		periodosOrdenados(p.periodo_base, p.periodo_atual),
	);
	const anuais = validos.filter((p) => meses(p.periodo_atual) === 12);
	return (anuais.length ? anuais : validos).reduce<ParPeriodos | undefined>(
		(melhor, p) =>
			!melhor || p.periodo_atual > melhor.periodo_atual ? p : melhor,
		undefined,
	);
}

/** Bases gravadas para um período atual, da mais recente para a mais antiga. */
export function basesDoAtual(pares: ParPeriodos[], atual: string): string[] {
	return pares
		.filter(
			(p) =>
				p.periodo_atual === atual && periodosOrdenados(p.periodo_base, atual),
		)
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
	const atuais = new Set(
		pares
			.filter((p) => periodosOrdenados(p.periodo_base, p.periodo_atual))
			.map((p) => p.periodo_atual),
	);
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

/** "2025-03" → "2025-03/2025-03": um mês no formato de período da URL e da API. */
export const periodoDoMes = (competencia: string) =>
	`${competencia}/${competencia}`;

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

/**
 * Par que a tela abre sem escolha na URL: o mês mais recente contra o mesmo mês do ano
 * anterior; sem ele, o mês anterior. A série vem em ordem, do mais antigo ao mais recente.
 */
export function parPadraoMensal(
	competencias: string[],
): ParPeriodos | undefined {
	for (const atual of [...competencias].reverse()) {
		const par = parDoMes(competencias, atual);
		if (par) return par;
	}
	return undefined;
}
