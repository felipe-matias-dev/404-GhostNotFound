import { describe, expect, it } from "vitest";
import { type DestinoPortal, lerFiltrosCompartilhados } from "#/lib/filtros";
import {
	type BuscaDaTela,
	buscaPara,
	destinoDe,
	registrar,
	telaDaNavegacao,
} from "../memoria";

const par = {
	periodo_base: "2024-01/2024-03",
	periodo_atual: "2025-01/2025-03",
};

const tela = (
	destino: DestinoPortal,
	search: Record<string, unknown>,
): BuscaDaTela => ({
	destino,
	search,
	filtros: lerFiltrosCompartilhados(destino, search),
});

const perdas = {
	...par,
	municipio: "Paulista",
	bairro: "Janga",
	classe: "B1",
	status: "aberta",
	secao: "fila",
	queda_min: 20,
	queda_max: 80,
	pagina: 3,
	ordenar_por: "prioridade",
} as const;

describe("registrar", () => {
	it("lembra só os campos locais de cada tela", () => {
		const memoria = registrar({}, "/perdas", perdas);
		expect(memoria["/perdas"]?.search).toEqual({
			status: "aberta",
			secao: "fila",
			queda_min: 20,
			queda_max: 80,
			pagina: 3,
			ordenar_por: "prioridade",
		});
		expect(memoria["/perdas"]?.filtros.municipio).toBe("Paulista");
		expect(memoria["/receita"]).toBeUndefined();
	});

	it("não guarda nada que não seja filtro na tela inicial", () => {
		expect(
			registrar({}, "/", { ...par, municipio: "Paulista" })["/"]?.search,
		).toEqual({});
	});

	it("reconhece apenas as telas com contrato de filtros", () => {
		expect(destinoDe("/receita")).toBe("/receita");
		expect(destinoDe("/perdas")).toBe("/perdas");
		expect(destinoDe("/login")).toBeUndefined();
		expect(destinoDe("/receita/")).toBeUndefined();
	});
});

describe("telaDaNavegacao", () => {
	it("durante a navegação usa a tela que está sendo montada", () => {
		const tela = telaDaNavegacao({
			isLoading: true,
			resolvedLocation: { pathname: "/perdas" },
			location: { pathname: "/receita" },
			matches: [
				{ pathname: "/", search: {} },
				{ pathname: "/receita", search: par },
			],
		});
		expect(tela).toEqual({
			pathname: "/receita",
			destino: "/receita",
			search: par,
		});
	});

	it("parada, a URL resolvida manda e um endereço sem tela não interpreta filtros", () => {
		const semTela = telaDaNavegacao({
			isLoading: false,
			resolvedLocation: { pathname: "/nao-existe" },
			location: { pathname: "/nao-existe" },
			matches: [{ pathname: "/", search: perdas }],
		});
		expect(semTela.pathname).toBe("/nao-existe");
		expect(semTela.destino).toBeUndefined();
		expect(semTela.search).toEqual({});
	});

	it("numa tela analítica parada, entrega a busca validada do match", () => {
		const tela = telaDaNavegacao({
			isLoading: false,
			resolvedLocation: { pathname: "/perdas" },
			location: { pathname: "/perdas" },
			matches: [
				{ pathname: "/", search: {} },
				{ pathname: "/perdas", search: perdas },
			],
		});
		expect(tela).toEqual({
			pathname: "/perdas",
			destino: "/perdas",
			search: perdas,
		});
	});
});

describe("buscaPara", () => {
	it("leva de Perdas à Receita só o compartilhado, sem os sinais locais", () => {
		const memoria = registrar({}, "/perdas", perdas);
		const receita = buscaPara("/receita", tela("/perdas", perdas), memoria, {
			efeito: "tarifa",
		});
		expect(receita).toMatchObject({
			...par,
			municipio: "Paulista",
			bairro: "Janga",
			classe: "B1",
			efeito: "tarifa",
		});
		for (const campo of [
			"status",
			"secao",
			"queda_min",
			"queda_max",
			"pagina",
			"ordenar_por",
		]) {
			expect(receita[campo]).toBeUndefined();
		}
	});

	it("ao voltar a Perdas recupera os sinais e usa o compartilhado mais recente", () => {
		const memoria = registrar({}, "/perdas", perdas);
		const receita = tela("/receita", {
			...par,
			municipio: "Recife",
			classe: "B1",
		});
		const volta = buscaPara("/perdas", receita, memoria);
		expect(volta).toMatchObject({
			...par,
			municipio: "Recife",
			classe: "B1",
			status: "aberta",
			secao: "fila",
			queda_min: 20,
			queda_max: 80,
		});
		expect(volta.bairro).toBeUndefined();
		expect(volta.pagina).toBeUndefined();
	});

	it("mantém a página de Perdas quando o recorte não mudou", () => {
		const memoria = registrar({}, "/perdas", perdas);
		const receita = tela("/receita", { ...perdas, status: undefined });
		expect(buscaPara("/perdas", receita, memoria).pagina).toBe(3);
	});

	it("fecha o painel da Rede quando período ou recorte mudam, sem perder o critério", () => {
		const memoria = registrar({}, "/rede", {
			periodo_base: par.periodo_base,
			inicio: "2025-01",
			fim: "2025-03",
			municipio: "Paulista",
			bairro: "Janga",
			criterio: "fec",
			visao: "localidades",
			alimentador: "AL-01",
			serie: "dec",
		});
		const receita = tela("/receita", {
			municipio: "Paulista",
			bairro: "Janga",
			periodo_base: "2023-01/2023-03",
			periodo_atual: "2024-01/2024-03",
		});
		const volta = buscaPara("/rede", receita, memoria);
		expect(volta).toMatchObject({
			criterio: "fec",
			visao: "localidades",
			municipio: "Paulista",
			bairro: "Janga",
			periodo_base: "2023-01/2023-03",
			inicio: "2024-01",
			fim: "2024-03",
		});
		expect(volta.alimentador).toBeUndefined();
		expect(volta.serie).toBeUndefined();
		expect(volta.periodo_atual).toBeUndefined();
	});

	it("mantém o painel da Rede no mesmo período e recorte", () => {
		const memoria = registrar({}, "/rede", {
			periodo_base: par.periodo_base,
			inicio: "2025-01",
			fim: "2025-03",
			municipio: "Paulista",
			alimentador: "AL-01",
			serie: "fec",
		});
		const receita = tela("/receita", { ...par, municipio: "Paulista" });
		const volta = buscaPara("/rede", receita, memoria);
		expect(volta.alimentador).toBe("AL-01");
		expect(volta.serie).toBe("fec");
	});

	it("na própria tela a URL validada manda, sem mesclar a memória", () => {
		const memoria = registrar({}, "/receita", { ...par, efeito: "tarifa" });
		const atual = tela("/receita", { ...par, efeito: "volume" });
		const mesma = buscaPara("/receita", atual, memoria);
		expect(mesma.efeito).toBe("volume");
		expect(mesma.periodo_atual).toBe(par.periodo_atual);
	});

	it("na própria tela não traz de volta filtros que a URL não tem", () => {
		const memoria = registrar({}, "/perdas", perdas);
		const mesma = buscaPara("/perdas", tela("/perdas", par), memoria);
		expect(mesma.status).toBeUndefined();
		expect(mesma.pagina).toBeUndefined();
		expect(mesma.periodo_atual).toBe(par.periodo_atual);
	});

	it("limpar sinais locais preserva o compartilhado", () => {
		const limpo = buscaPara(
			"/perdas",
			tela("/perdas", perdas),
			{},
			{
				status: undefined,
				queda_min: undefined,
				queda_max: undefined,
			},
		);
		expect(limpo.status).toBeUndefined();
		expect(limpo.queda_min).toBeUndefined();
		expect(limpo.queda_max).toBeUndefined();
		expect(limpo).toMatchObject({
			...par,
			municipio: "Paulista",
			bairro: "Janga",
			classe: "B1",
		});
	});

	it("limpar o recorte zera a página, mantém os sinais e o período", () => {
		const limpo = buscaPara(
			"/perdas",
			tela("/perdas", perdas),
			{},
			{
				municipio: undefined,
				bairro: undefined,
				classe: undefined,
			},
		);
		expect(limpo.municipio).toBeUndefined();
		expect(limpo.bairro).toBeUndefined();
		expect(limpo.classe).toBeUndefined();
		expect(limpo.status).toBe("aberta");
		expect(limpo.pagina).toBeUndefined();
		expect(limpo.periodo_atual).toBe(par.periodo_atual);
	});

	it("trocar o município limpa o bairro e preserva classe, período e efeito", () => {
		const atual = tela("/receita", { ...perdas, efeito: "tarifa" });
		const trocado = buscaPara("/receita", atual, {}, { municipio: "Recife" });
		expect(trocado).toMatchObject({
			...par,
			municipio: "Recife",
			classe: "B1",
			efeito: "tarifa",
		});
		expect(trocado.bairro).toBeUndefined();
	});

	it("leva cod_uc à consulta individual sem os filtros exclusivos de Perdas", () => {
		const uc = buscaPara(
			"/uc",
			tela("/perdas", perdas),
			{},
			{
				cod_uc: "0005",
			},
		);
		expect(uc.cod_uc).toBe("0005");
		expect(uc.status).toBeUndefined();
		expect(uc.pagina).toBeUndefined();
		expect(uc.periodo_atual).toBe(par.periodo_atual);
	});

	it("sem memória do destino, leva só o compartilhado", () => {
		const volta = buscaPara("/perdas", tela("/receita", par), {});
		expect(volta).toMatchObject(par);
		expect(volta.status).toBeUndefined();
		expect(volta.pagina).toBeUndefined();
	});
});
