import {
	aplicarPatch,
	type DestinoPortal,
	type FiltrosCompartilhados,
	gravarFiltrosCompartilhados,
	lerFiltrosCompartilhados,
} from "#/lib/filtros";

/**
 * Campos da URL que pertencem só à tela. A memória do portal guarda exatamente estes: nada de
 * seleções de linha, modais, erros ou resultados de mutation, que não voltam ao reabrir.
 */
export const CAMPOS_LOCAIS: Record<DestinoPortal, readonly string[]> = {
	"/": [],
	"/receita": ["efeito"],
	"/rede": ["criterio", "visao", "alimentador", "serie"],
	"/perdas": [
		"status",
		"secao",
		"queda_min",
		"queda_max",
		"medidor_eletromecanico",
		"leituras_estimadas_min",
		"leituras_estimadas_max",
		"pagina",
		"ordenar_por",
		"direcao",
	],
	"/uc": ["cod_uc"],
};

/** Busca local de uma tela no momento em que ela fica estável, com o contexto compartilhado. */
export type Snapshot = {
	search: Record<string, unknown>;
	filtros: FiltrosCompartilhados;
};

export type Memoria = Partial<Record<DestinoPortal, Snapshot>>;

/** A tela aberta: busca validada e filtros compartilhados que a URL manda. */
export type BuscaDaTela = {
	/** `undefined` em telas sem contrato de filtros (login, 404): nenhuma é a tela atual. */
	destino: DestinoPortal | undefined;
	search: Record<string, unknown>;
	filtros: FiltrosCompartilhados;
};

export function destinoDe(pathname: string): DestinoPortal | undefined {
	return Object.hasOwn(CAMPOS_LOCAIS, pathname)
		? (pathname as DestinoPortal)
		: undefined;
}

/** O mínimo do estado do Router que decide qual tela está aberta. */
export type EstadoDaNavegacao = {
	isLoading: boolean;
	resolvedLocation?: { pathname: string };
	matches: readonly { pathname: string; search: unknown }[];
	location: { pathname: string };
};

/**
 * Tela corrente sem estado misto. Durante uma navegação, o match que está sendo montado manda
 * (a URL resolvida ainda é a anterior); parada, vale a URL resolvida, que também revela um
 * endereço sem tela — ali não há filtros a interpretar.
 */
export function telaDaNavegacao(estado: EstadoDaNavegacao): {
	pathname: string;
	destino: DestinoPortal | undefined;
	search: Record<string, unknown>;
} {
	const folha = estado.matches.at(-1);
	const pathname =
		estado.isLoading || !estado.resolvedLocation
			? (folha?.pathname ?? estado.location.pathname)
			: estado.resolvedLocation.pathname;
	const destino = destinoDe(pathname);
	return {
		pathname,
		destino,
		search: destino && folha ? (folha.search as Record<string, unknown>) : {},
	};
}

function selecionar(
	search: Record<string, unknown>,
	campos: readonly string[],
): Record<string, unknown> {
	return Object.fromEntries(
		campos
			.filter((campo) => search[campo] !== undefined)
			.map((campo) => [campo, search[campo]]),
	);
}

/** Guarda a busca local da tela concluída; os campos compartilhados ficam fora da memória. */
export function registrar(
	memoria: Memoria,
	destino: DestinoPortal,
	search: Record<string, unknown>,
): Memoria {
	return {
		...memoria,
		[destino]: {
			search: selecionar(search, CAMPOS_LOCAIS[destino]),
			filtros: lerFiltrosCompartilhados(destino, search),
		},
	};
}

const mudouRecorte = (
	antes: FiltrosCompartilhados,
	agora: FiltrosCompartilhados,
) =>
	antes.municipio !== agora.municipio ||
	antes.bairro !== agora.bairro ||
	antes.classe !== agora.classe;

/**
 * O que ainda vale da última visita. Página e painel do alimentador dependem do recorte e do
 * período com que foram abertos; os demais filtros locais continuam valendo.
 */
function locaisAindaValidos(
	destino: DestinoPortal,
	snapshot: Snapshot | undefined,
	agora: FiltrosCompartilhados,
): Record<string, unknown> {
	if (!snapshot) return {};
	const local = { ...snapshot.search };
	const antes = snapshot.filtros;
	if (destino === "/perdas" && mudouRecorte(antes, agora)) {
		delete local.pagina;
	}
	if (
		destino === "/rede" &&
		(mudouRecorte(antes, agora) ||
			antes.periodo_base !== agora.periodo_base ||
			antes.periodo_atual !== agora.periodo_atual)
	) {
		delete local.alimentador;
		delete local.serie;
	}
	return local;
}

/**
 * Busca de um link entre telas. Na própria tela a URL validada é a fonte da verdade, sem
 * sobreposição da memória; em outra, entram só os locais lembrados do destino e o
 * compartilhado atual. O patch explícito do chamador vence no fim, inclusive remoções.
 */
export function buscaPara(
	alvo: DestinoPortal,
	atual: BuscaDaTela,
	memoria: Memoria,
	patch: Record<string, unknown> = {},
): Record<string, unknown> {
	const filtros = aplicarPatch(atual.filtros, patch);
	const local =
		alvo === atual.destino
			? locaisAindaValidos(
					alvo,
					{
						search: selecionar(atual.search, CAMPOS_LOCAIS[alvo]),
						filtros: atual.filtros,
					},
					filtros,
				)
			: locaisAindaValidos(alvo, memoria[alvo], filtros);
	const busca: Record<string, unknown> = {
		...local,
		...gravarFiltrosCompartilhados(alvo, filtros),
		...patch,
	};
	// `/rede` escreve o período como duas pontas; o par inteiro não convive com elas.
	if (alvo === "/rede") {
		delete busca.periodo_atual;
	} else {
		delete busca.inicio;
		delete busca.fim;
	}
	return busca;
}
