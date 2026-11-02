import { describe, expect, it } from "vitest";
import { agruparOrdensKanban, limiteFinalizadas } from "../conversions";
import type { Ordem } from "../types";

const BASE: Omit<Ordem, "id" | "status"> = {
	cod_uc: "0001",
	resultado: null,
	observacao: null,
	criada_em: "2026-10-01T00:00:00Z",
	atualizada_em: "2026-10-01T00:00:00Z",
	no_status_desde: "2026-10-01T00:00:00Z",
	segundos_no_status: 0,
	atrasada: false,
};

function ordem(mudanca: Partial<Ordem> & Pick<Ordem, "id" | "status">): Ordem {
	return { ...BASE, ...mudanca };
}

describe("limiteFinalizadas", () => {
	it("usa 3 abaixo de 900 px", () => {
		expect(limiteFinalizadas(0)).toBe(3);
		expect(limiteFinalizadas(768)).toBe(3);
		expect(limiteFinalizadas(899)).toBe(3);
	});

	it("usa 5 de 900 a 1299 px", () => {
		expect(limiteFinalizadas(900)).toBe(5);
		expect(limiteFinalizadas(1080)).toBe(5);
		expect(limiteFinalizadas(1299)).toBe(5);
	});

	it("usa 8 a partir de 1300 px", () => {
		expect(limiteFinalizadas(1300)).toBe(8);
		expect(limiteFinalizadas(1440)).toBe(8);
	});
});

describe("agruparOrdensKanban", () => {
	it("mantém as ativas na ordem recebida e corta as finalizadas pelas mais recentes", () => {
		const grupos = agruparOrdensKanban(
			[
				ordem({ id: 30, status: "GERADA" }),
				ordem({
					id: 10,
					status: "CONCLUIDA",
					atualizada_em: "2026-10-01T10:00:00Z",
				}),
				ordem({ id: 31, status: "EM_CAMPO" }),
				ordem({
					id: 12,
					status: "CONCLUIDA",
					atualizada_em: "2026-10-03T10:00:00Z",
				}),
				ordem({
					id: 11,
					status: "CONCLUIDA",
					atualizada_em: "2026-10-02T10:00:00Z",
				}),
				ordem({
					id: 13,
					status: "CONCLUIDA",
					atualizada_em: "2026-10-03T10:00:00Z",
				}),
			],
			2,
		);

		expect(grupos.GERADA.map((o) => o.id)).toEqual([30]);
		expect(grupos.EM_CAMPO.map((o) => o.id)).toEqual([31]);
		// Empate em atualizada_em: id decrescente.
		expect(grupos.CONCLUIDA.visiveis.map((o) => o.id)).toEqual([13, 12]);
		expect(grupos.CONCLUIDA.total).toBe(4);
		expect(grupos.CANCELADA).toEqual({ visiveis: [], total: 0 });
	});

	it("conta todas as canceladas antes do corte", () => {
		const grupos = agruparOrdensKanban(
			[
				ordem({
					id: 1,
					status: "CANCELADA",
					atualizada_em: "2026-10-01T10:00:00Z",
				}),
				ordem({
					id: 2,
					status: "CANCELADA",
					atualizada_em: "2026-10-03T10:00:00Z",
				}),
				ordem({
					id: 3,
					status: "CANCELADA",
					atualizada_em: "2026-10-02T10:00:00Z",
				}),
			],
			1,
		);

		expect(grupos.CANCELADA.visiveis.map((o) => o.id)).toEqual([2]);
		expect(grupos.CANCELADA.total).toBe(3);
	});

	it("não muta o array nem as ordens recebidas", () => {
		const ordens = [
			ordem({ id: 1, status: "GERADA" }),
			ordem({
				id: 2,
				status: "CONCLUIDA",
				atualizada_em: "2026-10-02T10:00:00Z",
			}),
			ordem({
				id: 3,
				status: "CONCLUIDA",
				atualizada_em: "2026-10-03T10:00:00Z",
			}),
		];
		const copia = ordens.map((o) => ({ ...o }));

		agruparOrdensKanban(ordens, 1);

		expect(ordens).toEqual(copia);
	});
});
