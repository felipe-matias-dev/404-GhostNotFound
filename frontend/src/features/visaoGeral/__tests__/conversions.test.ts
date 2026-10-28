import { describe, expect, it } from "vitest";
import {
	efeitosDaReceita,
	janelasDaBase,
	leitura,
	parDoMes,
	parEscolhido,
	parPadrao,
	tesoura,
} from "../conversions";
import type { JanelaIndicadores, ParPeriodos } from "../types";

const par = (base: string, atual: string): ParPeriodos => ({
	periodo_base: `${base}/${base}`,
	periodo_atual: `${atual}/${atual}`,
});

const meses = (inicio: string, quantos: number) => {
	const [ano, mes] = inicio.split("-").map(Number);
	return Array.from({ length: quantos }, (_, i) => {
		const total = ano * 12 + mes - 1 + i;
		return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, "0")}`;
	});
};

describe("parPadrao", () => {
	it("compara o mês mais recente com o mesmo mês do ano anterior", () => {
		expect(parPadrao(meses("2024-01", 24))).toEqual(par("2024-12", "2025-12"));
	});

	it("usa o mês anterior quando a série tem menos de um ano", () => {
		expect(parPadrao(meses("2025-01", 6))).toEqual(par("2025-05", "2025-06"));
	});

	it("não compara nada com um mês só", () => {
		expect(parPadrao(["2025-01"])).toBeUndefined();
	});
});

describe("parDoMes", () => {
	const competencias = meses("2024-01", 24);

	it("mantém a relação pedida quando a base existe", () => {
		expect(parDoMes(competencias, "2025-03", "mes")).toEqual(
			par("2025-02", "2025-03"),
		);
	});

	it("troca de relação quando a base pedida está fora da série", () => {
		expect(parDoMes(competencias, "2024-03", "ano")).toEqual(
			par("2024-02", "2024-03"),
		);
	});

	it("vira o ano no mês anterior de janeiro", () => {
		expect(parDoMes(competencias, "2025-01", "mes")).toEqual(
			par("2024-12", "2025-01"),
		);
	});
});

describe("parEscolhido", () => {
	const competencias = meses("2024-01", 24);

	it("aceita da URL dois meses da série, com a base antes do atual", () => {
		expect(
			parEscolhido(competencias, "2024-03/2024-03", "2025-07/2025-07"),
		).toEqual(par("2024-03", "2025-07"));
	});

	it.each([
		["trecho de vários meses", "2024-01/2024-12", "2025-01/2025-12"],
		["mês fora da série", "2023-12/2023-12", "2024-12/2024-12"],
		["base depois do atual", "2025-07/2025-07", "2024-07/2024-07"],
		["sem par na URL", undefined, undefined],
	])("volta ao padrão com %s", (_, base, atual) => {
		expect(parEscolhido(competencias, base, atual)).toEqual(
			par("2024-12", "2025-12"),
		);
	});
});

const janela = (
	inicio: string,
	fim: string,
	receita: number,
	kwh: number,
): JanelaIndicadores => ({
	inicio,
	fim,
	receita_faturada: receita,
	receita_energia: receita,
	kwh_faturado: kwh,
	n_uc_medio: 10,
	tarifa_media: receita / kwh,
	tarifa_base_media: receita / kwh,
});

describe("janelasDaBase", () => {
	it("compara a primeira e a última janela completa retornadas pelo backend", () => {
		expect(
			janelasDaBase([
				janela("2022-01", "2022-12", 120, 1200),
				janela("2022-02", "2023-01", 130, 1250),
				janela("2025-01", "2025-12", 150, 1400),
			]),
		).toEqual({
			base: "2022-01/2022-12",
			atual: "2025-01/2025-12",
		});
	});

	it("não compara janelas sobrepostas nem série sem janela completa", () => {
		expect(janelasDaBase([])).toBeUndefined();
		expect(
			janelasDaBase([
				janela("2024-01", "2024-12", 120, 1200),
				janela("2024-12", "2025-11", 150, 1400),
			]),
		).toBeUndefined();
	});
});

describe("tesoura", () => {
	it("mede a variação das somas recebidas sem acumular novamente as janelas", () => {
		const t = tesoura([
			janela("2024-01", "2024-12", 120, 1200),
			janela("2024-02", "2025-01", 132, 1176),
		]);
		expect(t.categories.map((c) => c.key)).toEqual(["2024-12", "2025-01"]);
		expect(t.series[0].values).toEqual([0, expect.closeTo(0.1)]);
		expect(t.series[1].values).toEqual([0, expect.closeTo(-0.02)]);
		expect(t.somas[1]).toEqual({ receita: 132, kwh: 1176 });
	});

	it("mantém os meses retornados mesmo quando há um intervalo sem janelas", () => {
		expect(
			tesoura([
				janela("2024-01", "2024-12", 120, 1200),
				janela("2024-04", "2025-03", 132, 1176),
			]).categories.map((c) => c.key),
		).toEqual(["2024-12", "2025-03"]);
		expect(tesoura([janela("2024-01", "2024-12", 120, 1200)]).series).toEqual(
			[],
		);
	});

	it("não inventa variação para uma série cuja primeira soma é zero", () => {
		const t = tesoura([
			janela("2024-01", "2024-12", 0, 1200),
			janela("2024-02", "2025-01", 132, 1176),
		]);
		expect(t.series[0].values).toEqual([null, null]);
		expect(t.series[1].values[1]).toBeCloseTo(-0.02);
	});
});

describe("leitura", () => {
	it("descreve a tesoura pela direção das duas variações", () => {
		expect(leitura(8, -4)).toBe(
			"A receita cresceu com menos energia faturada.",
		);
		expect(leitura(3, 5)).toBe(
			"A receita cresceu menos que a energia faturada.",
		);
		expect(leitura(-5, -2)).toBe("A receita caiu mais que a energia faturada.");
	});

	it("trata como estável a variação que arredonda para 0,0%", () => {
		expect(leitura(0.04, -3)).toBe(
			"A receita ficou estável com menos energia faturada.",
		);
		expect(leitura(null, 2)).toBeNull();
	});
});

describe("efeitosDaReceita", () => {
	it("dá o peso de cada efeito sobre a receita base, sem os totais", () => {
		const efeitos = efeitosDaReceita([
			{ id: "base", label: "Receita base", value: 200, kind: "total" },
			{ id: "tarifa", label: "Preço · tarifa", value: 16, kind: "delta" },
			{ id: "volume", label: "Volume", value: -6, kind: "delta" },
			{ id: "atual", label: "Receita atual", value: 210, kind: "total" },
		]);
		expect(efeitos.map((e) => [e.id, e.pct])).toEqual([
			["tarifa", 0.08],
			["volume", -0.03],
		]);
	});

	it("não dá peso sem receita base", () => {
		const [efeito] = efeitosDaReceita([
			{ id: "base", label: "Receita base", value: 0, kind: "total" },
			{ id: "tarifa", label: "Preço · tarifa", value: 5, kind: "delta" },
		]);
		expect(efeito?.pct).toBeNull();
	});
});
