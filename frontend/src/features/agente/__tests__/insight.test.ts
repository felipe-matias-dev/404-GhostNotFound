import { describe, expect, it } from "vitest";
import { indisponivelDoInsight } from "../insight";

describe("indisponivelDoInsight", () => {
	it("não é indisponível antes do primeiro pedido", () => {
		expect(indisponivelDoInsight({ isError: false, data: undefined })).toBe(
			false,
		);
	});

	it("é indisponível quando a busca falhou", () => {
		expect(indisponivelDoInsight({ isError: true, data: undefined })).toBe(
			true,
		);
	});

	it("é indisponível quando a resposta veio sem texto", () => {
		expect(
			indisponivelDoInsight({ isError: false, data: { texto: null } }),
		).toBe(true);
		expect(indisponivelDoInsight({ isError: false, data: { texto: "" } })).toBe(
			true,
		);
	});

	it("não é indisponível quando há texto", () => {
		expect(
			indisponivelDoInsight({ isError: false, data: { texto: "Um texto." } }),
		).toBe(false);
	});
});
