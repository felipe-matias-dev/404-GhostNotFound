import { describe, expect, it } from "vitest";
import { formatTempoDecorrido } from "../format";

describe("formatTempoDecorrido", () => {
	it("mostra segundos na primeira hora, e minutos com segundos de dois dígitos", () => {
		expect(formatTempoDecorrido(0)).toBe("0 s");
		expect(formatTempoDecorrido(42)).toBe("42 s");
		expect(formatTempoDecorrido(59)).toBe("59 s");
		expect(formatTempoDecorrido(60)).toBe("1 min 00 s");
		expect(formatTempoDecorrido(728)).toBe("12 min 08 s");
		expect(formatTempoDecorrido(3599)).toBe("59 min 59 s");
	});

	it("troca os segundos por minutos de dois dígitos a partir de uma hora", () => {
		expect(formatTempoDecorrido(3600)).toBe("1 h 00 min");
		expect(formatTempoDecorrido(12_000)).toBe("3 h 20 min");
		expect(formatTempoDecorrido(86_399)).toBe("23 h 59 min");
	});

	it("passa para dias e horas a partir de um dia", () => {
		expect(formatTempoDecorrido(86_400)).toBe("1 d 0 h");
		expect(formatTempoDecorrido(191_000)).toBe("2 d 5 h");
		expect(formatTempoDecorrido(11 * 86_400)).toBe("11 d 0 h");
	});

	it("descarta a fração e trata negativo ou inválido como zero", () => {
		expect(formatTempoDecorrido(42.9)).toBe("42 s");
		expect(formatTempoDecorrido(-5)).toBe("0 s");
		expect(formatTempoDecorrido(Number.NaN)).toBe("0 s");
	});
});
