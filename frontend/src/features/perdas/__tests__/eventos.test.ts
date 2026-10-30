import { describe, expect, it } from "vitest";
import { autorEvento, tituloEvento } from "../conversions";

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

describe("autorEvento", () => {
	it("mostra o nome de quem agiu", () => {
		expect(autorEvento({ autor_nome: "Rafael", autor_login: "rafael" })).toBe(
			"Rafael",
		);
	});

	it("cai no login quando o usuário não existe mais", () => {
		expect(autorEvento({ autor_nome: null, autor_login: "rafael" })).toBe(
			"rafael",
		);
	});

	it("não inventa autor nos eventos de antes do login", () => {
		expect(autorEvento({ autor_nome: null, autor_login: null })).toBeNull();
	});
});
