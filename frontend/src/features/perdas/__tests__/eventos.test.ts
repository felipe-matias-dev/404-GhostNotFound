import { describe, expect, it } from "vitest";
import { tituloEvento } from "../conversions";

describe("tituloEvento", () => {
	it("mostra a criação quando o evento não tem status anterior", () => {
		expect(
			tituloEvento({ status_anterior: null, status_novo: "GERADA" }),
		).toEqual({ origem: null, destino: "Gerada" });
	});

	it("usa os rótulos da tela na transição", () => {
		expect(
			tituloEvento({ status_anterior: "EM_CAMPO", status_novo: "CONCLUIDA" }),
		).toEqual({ origem: "Em campo", destino: "Concluída" });
	});
});
