import { describe, expect, it } from "vitest";
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
