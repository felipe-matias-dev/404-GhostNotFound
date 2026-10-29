import { describe, expect, it } from "vitest";
import { adicionarRecente, parseRecentes } from "../recentes";

describe("recent UC history", () => {
	it("moves a repeated UC to the front and retains only five unique codes", () => {
		expect(
			adicionarRecente(["0001", "0002", "0003", "0004", "0005"], "0003"),
		).toEqual(["0003", "0001", "0002", "0004", "0005"]);
		expect(
			adicionarRecente(["0001", "0002", "0003", "0004", "0005"], "0006"),
		).toEqual(["0006", "0001", "0002", "0003", "0004"]);
	});

	it("preserves identifier zeros, case and punctuation without storing customer objects", () => {
		expect(
			parseRecentes('["0001", "A-02", "a-02", "0001", " 003 ", "004", "005"]'),
		).toEqual(["0001", "A-02", "a-02", "003", "004"]);
		expect(parseRecentes('[{"cod_uc":"0001","titular":"Pessoa"}]')).toEqual([]);
	});

	it.each([
		null,
		"invalid json",
		"{}",
		'"0001"',
		'["0001", null]',
		'[""]',
		'["   "]',
	])("ignores malformed persisted history: %s", (raw) => {
		expect(parseRecentes(raw)).toEqual([]);
	});
});
