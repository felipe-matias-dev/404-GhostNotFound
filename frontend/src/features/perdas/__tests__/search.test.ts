import { describe, expect, it } from "vitest";
import { lerFiltrosCompartilhados } from "#/lib/filtros";
import {
	buscaCanonicaLocal,
	filtrosDaBusca,
	normalizacaoLocal,
	paginaDaBusca,
	patchDaOrdenacao,
	patchDaPagina,
	patchDosFiltros,
	perdasSearchSchema,
	recorteDaBusca,
	sortDaBusca,
} from "../search";

const buscar = (bruto: Record<string, unknown>) =>
	perdasSearchSchema.parse(bruto);

describe("perdasSearchSchema", () => {
	it("lê booleanos de texto sem tratar qualquer texto como verdadeiro", () => {
		expect(
			perdasSearchSchema.parse({ medidor_eletromecanico: "false" })
				.medidor_eletromecanico,
		).toBe(false);
		expect(
			perdasSearchSchema.parse({ medidor_eletromecanico: "true" })
				.medidor_eletromecanico,
		).toBe(true);
		expect(
			perdasSearchSchema.parse({ medidor_eletromecanico: "1" })
				.medidor_eletromecanico,
		).toBeUndefined();
	});

	it("descarta mês inexistente e faixa fora dos limites", () => {
		const invalido = perdasSearchSchema.parse({
			periodo_atual: "2025-13/2025-12",
		});
		expect(invalido.periodo_atual).toBe("2025-13/2025-12");
		expect(
			lerFiltrosCompartilhados("/perdas", invalido).periodo_atual,
		).toBeUndefined();
		expect(
			perdasSearchSchema.parse({ queda_min: "101" }).queda_min,
		).toBeUndefined();
		expect(
			perdasSearchSchema.parse({ leituras_estimadas_min: "24" })
				.leituras_estimadas_min,
		).toBeUndefined();
	});
});

describe("recorteDaBusca", () => {
	it("não envia bairro órfão, que o backend recusaria com 422", () => {
		expect(recorteDaBusca({ bairro: "Janga" })).toEqual({});
		expect(recorteDaBusca({ municipio: "Paulista", bairro: "Janga" })).toEqual({
			municipio: "Paulista",
			bairro: "Janga",
		});
	});

	it("mantém classe sem geografia", () => {
		expect(recorteDaBusca({ classe: "B1" })).toEqual({ classe: "B1" });
	});
});

describe("filtrosDaBusca", () => {
	it("sem parâmetros devolve os sinais desligados", () => {
		expect(filtrosDaBusca({})).toEqual({
			queda: null,
			medidorEletromecanico: false,
			leiturasEstimadas: null,
		});
	});

	it("completa uma ponta isolada com o limite correspondente", () => {
		expect(filtrosDaBusca({ queda_min: 20 }).queda).toEqual([20, 100]);
		expect(filtrosDaBusca({ queda_max: 80 }).queda).toEqual([0, 80]);
		expect(
			filtrosDaBusca({ leituras_estimadas_max: 60 }).leiturasEstimadas,
		).toEqual([25, 60]);
	});

	it("descarta a faixa invertida dos filtros", () => {
		const search = { queda_min: 80, queda_max: 20 } as const;
		expect(filtrosDaBusca(search).queda).toBeNull();
	});
});

describe("normalizacaoLocal", () => {
	it("não reescreve uma URL canônica", () => {
		const bruto = {
			queda_min: "20",
			queda_max: "80",
			medidor_eletromecanico: "true",
			leituras_estimadas_min: "25",
			leituras_estimadas_max: "60",
			pagina: "2",
			ordenar_por: "queda",
			direcao: "desc",
		};
		const resultado = normalizacaoLocal(bruto, buscar(bruto));
		expect(resultado.altera).toBe(false);
		expect(resultado.avisos).toEqual([]);
	});

	it("completa ponta isolada no filtro sem reescrever a URL", () => {
		const bruto = { queda_min: 20, leituras_estimadas_max: 60 };
		const resultado = normalizacaoLocal(bruto, buscar(bruto));
		expect(resultado.canonico.queda_max).toBe(100);
		expect(resultado.canonico.leituras_estimadas_min).toBe(25);
		expect(resultado.altera).toBe(false);
		expect(resultado.avisos).toEqual([]);
	});

	it("elimina faixa invertida da URL e avisa", () => {
		const bruto = {
			queda_min: 80,
			queda_max: 20,
			leituras_estimadas_min: 90,
			leituras_estimadas_max: 40,
		};
		const resultado = normalizacaoLocal(bruto, buscar(bruto));
		expect(resultado.altera).toBe(true);
		expect(resultado.canonico.queda_min).toBeUndefined();
		expect(resultado.canonico.queda_max).toBeUndefined();
		expect(resultado.canonico.leituras_estimadas_min).toBeUndefined();
		expect(resultado.canonico.leituras_estimadas_max).toBeUndefined();
		expect(resultado.avisos).toEqual([
			"Faixa de queda invertida ignorada: a mínima não pode passar da máxima.",
			"Faixa de leituras estimadas invertida ignorada: a mínima não pode passar da máxima.",
		]);
		expect(filtrosDaBusca(buscar(bruto))).toEqual({
			queda: null,
			medidorEletromecanico: false,
			leiturasEstimadas: null,
		});
	});

	it("ignora valores inválidos com aviso e sem enviá-los à API", () => {
		const bruto = {
			pagina: "abc",
			medidor_eletromecanico: "1",
			queda_min: "101",
		};
		const resultado = normalizacaoLocal(bruto, buscar(bruto));
		expect(resultado.altera).toBe(true);
		expect(resultado.avisos).toEqual([
			"Valores inválidos na URL foram ignorados: queda, medidor eletromecânico, página.",
		]);
		expect(resultado.canonico.queda_min).toBeUndefined();
		expect(resultado.canonico.pagina).toBeUndefined();
		expect(filtrosDaBusca(buscar(bruto))).toEqual({
			queda: null,
			medidorEletromecanico: false,
			leiturasEstimadas: null,
		});
	});

	it("omite defaults e campos redundantes sem aviso", () => {
		const bruto = {
			pagina: 1,
			medidor_eletromecanico: "false",
			ordenar_por: "prioridade",
			direcao: "desc",
		};
		const resultado = normalizacaoLocal(bruto, buscar(bruto));
		expect(resultado.altera).toBe(true);
		expect(resultado.avisos).toEqual([]);
		expect(resultado.canonico.pagina).toBeUndefined();
		expect(resultado.canonico.medidor_eletromecanico).toBeUndefined();
		expect(resultado.canonico.ordenar_por).toBeUndefined();
		expect(resultado.canonico.direcao).toBeUndefined();
	});
});

describe("buscaCanonicaLocal", () => {
	it("preserva status, seção e ordenação da API", () => {
		const search = buscar({
			status: "GERADA",
			secao: "ordens",
			pagina: 2,
			ordenar_por: "energia",
			direcao: "desc",
		});
		expect(buscaCanonicaLocal(search)).toMatchObject({
			status: "GERADA",
			secao: "ordens",
			pagina: 2,
			ordenar_por: "energia",
			direcao: "desc",
		});
	});
});

describe("paginação e ordenação da URL", () => {
	it("usa a primeira página por padrão", () => {
		expect(paginaDaBusca({})).toBe(1);
		expect(paginaDaBusca({ pagina: 3 })).toBe(3);
	});

	it("recupera a ordenação servida pela API", () => {
		expect(sortDaBusca({})).toBeNull();
		expect(sortDaBusca({ ordenar_por: "prioridade" })).toBeNull();
		expect(sortDaBusca({ ordenar_por: "queda", direcao: "desc" })).toEqual({
			columnId: "queda",
			direction: "desc",
		});
		expect(sortDaBusca({ ordenar_por: "energia" })).toEqual({
			columnId: "energia",
			direction: "asc",
		});
	});

	it("omite defaults e volta à primeira página nos patches", () => {
		expect(patchDaPagina(1)).toEqual({ pagina: undefined });
		expect(patchDaPagina(2)).toEqual({ pagina: 2 });
		expect(
			patchDaOrdenacao({ columnId: "energia", direction: "desc" }),
		).toEqual({ ordenar_por: "energia", direcao: "desc", pagina: undefined });
		expect(patchDaOrdenacao(null)).toEqual({
			ordenar_por: undefined,
			direcao: undefined,
			pagina: undefined,
		});
	});
});

describe("patchDosFiltros", () => {
	it("leva só os sinais locais, omite defaults e reinicia a página", () => {
		expect(
			patchDosFiltros({
				queda: [20, 80],
				medidorEletromecanico: true,
				leiturasEstimadas: null,
			}),
		).toEqual({
			queda_min: 20,
			queda_max: 80,
			medidor_eletromecanico: true,
			leituras_estimadas_min: undefined,
			leituras_estimadas_max: undefined,
			pagina: undefined,
		});
		expect(
			patchDosFiltros({
				queda: null,
				medidorEletromecanico: false,
				leiturasEstimadas: [25, 100],
			}),
		).toEqual({
			queda_min: undefined,
			queda_max: undefined,
			medidor_eletromecanico: undefined,
			leituras_estimadas_min: 25,
			leituras_estimadas_max: 100,
			pagina: undefined,
		});
	});
});
