import { describe, expect, it } from "vitest";
import { NAVEGACAO, organizarNavegacao } from "#/components/layout/app-sidebar";
import { loginDestination } from "../profiles";

describe("loginDestination", () => {
	it("preserves a local data deep link even outside the profile menu", () => {
		expect(
			loginDestination("atendimento", "/receita?municipio=Recife#comparacao"),
		).toBe("/receita?municipio=Recife#comparacao");
	});

	it.each([
		"https://example.com/uc",
		"//example.com/uc",
		"/\\example.com/uc",
		"javascript:alert(1)",
		"/login?redirect=/uc",
		"/uc/../../login",
	])("never follows an external or unknown return address: %s", (redirect) => {
		expect(loginDestination("perdas", redirect)).toBe("/perdas");
	});
});

describe("role navigation", () => {
	it("puts primary screens first without hiding or duplicating other screens", () => {
		const items = organizarNavegacao(NAVEGACAO, ["/perdas", "/uc"]);

		expect(items.map(({ to, grupo }) => [to, grupo])).toEqual([
			["/uc", "Minha área"],
			["/perdas", "Minha área"],
			["/", "Outras consultas"],
			["/receita", "Outras consultas"],
			["/rede", "Outras consultas"],
		]);
	});

	it.each([
		{ primary: [], group: "Outras consultas" },
		{ primary: NAVEGACAO.map(({ to }) => to), group: "Minha área" },
	])("keeps all screens when every item belongs to $group", ({
		primary,
		group,
	}) => {
		const items = organizarNavegacao(NAVEGACAO, primary);

		expect(items.map(({ to }) => to)).toEqual(NAVEGACAO.map(({ to }) => to));
		expect(new Set(items.map(({ grupo }) => grupo))).toEqual(new Set([group]));
	});
});
