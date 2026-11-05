import { describe, expect, it } from "vitest";
import { ApiError } from "#/lib/api";
import {
	desfazerAlteracao,
	ESCOPOS_AGENTE,
	EXEMPLOS_PERGUNTAS,
	extrairMensagemErro,
	filtrarExemplosPorEscopo,
	formatarCelulaResultado,
	formatarSessaoComoMarkdown,
	gerarTituloSessao,
	MAX_PERGUNTA_CHARS,
	mesclarSessoes,
	nomeAmigavelView,
	reinserirSessao,
	rotuloConfianca,
	rotuloStatusResposta,
	sessaoDaApi,
	validarPergunta,
} from "../conversions";
import type { ExemploPergunta, RespostaIa, SessaoConversa } from "../types";

function resposta(answer = "Receita faturada: R$ 1.000,00"): RespostaIa {
	return {
		audit_id: 1,
		answer,
		status: "answered",
		sql: "select 1",
		rows: [],
		row_count: 0,
		truncated: false,
		confidence: "high",
		sources: ["sem_faturamento_mensal"],
		assumptions: [],
		clarification: null,
		refused_reason: null,
		request_id: "req-1",
		model: "gemini",
		prompt_version: "v1",
		latency_ms: 900,
		input_tokens: 0,
		output_tokens: 0,
		column_units: {},
		column_labels: {},
		session_id: "sessao-1",
	};
}

function sessao(sessionId: string, titulo = "Conversa"): SessaoConversa {
	return {
		sessionId,
		titulo,
		criadaEm: "2026-10-01T10:00:00.000Z",
		atualizadaEm: "2026-10-01T10:05:00.000Z",
		turnos: [
			{
				id: `${sessionId}-turno`,
				question: "Qual foi a receita em setembro de 2025?",
				criadoEm: "2026-10-01T10:00:00.000Z",
				status: "completed",
				resposta: resposta(),
			},
		],
	};
}

describe("gerarTituloSessao", () => {
	it("devolve o título padrão sem pergunta", () => {
		expect(gerarTituloSessao("")).toBe("Nova conversa");
		expect(gerarTituloSessao("   ")).toBe("Nova conversa");
	});

	it("junta os espaços e apara as pontas", () => {
		expect(gerarTituloSessao("  Qual a receita\n de setembro?  ")).toBe(
			"Qual a receita de setembro?",
		);
	});

	it("mantém a pergunta curta inteira", () => {
		const pergunta = "a".repeat(48);
		expect(gerarTituloSessao(pergunta)).toBe(pergunta);
	});

	it("corta em 48 caracteres com reticências", () => {
		const titulo = gerarTituloSessao("a".repeat(80));
		expect(titulo).toBe(`${"a".repeat(47)}…`);
		expect(titulo).toHaveLength(48);
	});
});

describe("validarPergunta", () => {
	it("recusa pergunta vazia", () => {
		expect(validarPergunta("")).toEqual({
			ok: false,
			erro: "Escreva uma pergunta para o agente.",
		});
		expect(validarPergunta("  \n ")).toMatchObject({ ok: false });
	});

	it("apara a pergunta antes de enviar", () => {
		expect(validarPergunta("  Qual o DEC de Olinda?  ")).toEqual({
			ok: true,
			question: "Qual o DEC de Olinda?",
		});
	});

	it("aceita até o limite e recusa acima dele", () => {
		expect(validarPergunta("a".repeat(MAX_PERGUNTA_CHARS))).toMatchObject({
			ok: true,
		});
		expect(validarPergunta("a".repeat(MAX_PERGUNTA_CHARS + 1))).toEqual({
			ok: false,
			erro: `A pergunta pode ter até ${MAX_PERGUNTA_CHARS} caracteres.`,
		});
	});
});

describe("filtrarExemplosPorEscopo", () => {
	const exemplos: readonly ExemploPergunta[] = EXEMPLOS_PERGUNTAS;

	it("devolve todos os exemplos em Todos os dados", () => {
		expect(filtrarExemplosPorEscopo(exemplos, "Todos os dados")).toBe(exemplos);
	});

	it("filtra pelo escopo escolhido", () => {
		const receita = filtrarExemplosPorEscopo(exemplos, "Receita e faturamento");
		expect(receita.length).toBeGreaterThan(0);
		expect(
			receita.every((item) => item.escopo === "Receita e faturamento"),
		).toBe(true);
	});

	it("cobre todos os escopos do seletor", () => {
		for (const escopo of ESCOPOS_AGENTE) {
			if (escopo === "Todos os dados") continue;
			expect(filtrarExemplosPorEscopo(exemplos, escopo).length).toBeGreaterThan(
				0,
			);
		}
	});
});

describe("rotuloConfianca", () => {
	it("traduz cada grau de confiança", () => {
		expect(rotuloConfianca("high")).toEqual({
			rotulo: "Confiança alta",
			tom: "success",
		});
		expect(rotuloConfianca("medium")).toEqual({
			rotulo: "Confiança média",
			tom: "warning",
		});
		expect(rotuloConfianca("low")).toEqual({
			rotulo: "Confiança baixa",
			tom: "warning",
		});
		expect(rotuloConfianca("unknown")).toEqual({
			rotulo: "Sem grau de confiança",
			tom: "neutral",
		});
	});
});

describe("rotuloStatusResposta", () => {
	it("traduz cada status do agente", () => {
		expect(rotuloStatusResposta("answered")).toEqual({
			rotulo: "Respondida",
			tom: "success",
		});
		expect(rotuloStatusResposta("clarify")).toEqual({
			rotulo: "Precisa de esclarecimento",
			tom: "info",
		});
		expect(rotuloStatusResposta("unknown")).toEqual({
			rotulo: "Fora da camada de dados",
			tom: "warning",
		});
		expect(rotuloStatusResposta("refused")).toEqual({
			rotulo: "Consulta recusada",
			tom: "danger",
		});
		expect(rotuloStatusResposta("failed")).toEqual({
			rotulo: "Falha na consulta",
			tom: "danger",
		});
	});
});

describe("nomeAmigavelView", () => {
	it("traduz as views da camada semântica", () => {
		expect(nomeAmigavelView("sem_uc")).toBe("Cadastro de UCs");
		expect(nomeAmigavelView("sem_receita_decomposicao")).toBe(
			"Decomposição de receita",
		);
	});

	it("mantém o nome técnico quando a view é desconhecida", () => {
		expect(nomeAmigavelView("sem_nova")).toBe("sem_nova");
	});
});

describe("formatarCelulaResultado", () => {
	it("mostra traço para valor ausente", () => {
		expect(formatarCelulaResultado("receita_faturada", null)).toBe("—");
		expect(formatarCelulaResultado("receita_faturada", undefined)).toBe("—");
	});

	it("traduz booleano", () => {
		expect(formatarCelulaResultado("possui_gd", true)).toBe("Sim");
		expect(formatarCelulaResultado("possui_gd", false)).toBe("Não");
	});

	it("formata competência, data e texto livre", () => {
		expect(formatarCelulaResultado("competencia", "2025-03")).toBe("mar/2025");
		expect(formatarCelulaResultado("data_ligacao", "2025-03-10")).toBe(
			"10/03/2025",
		);
		expect(formatarCelulaResultado("municipio", "Recife")).toBe("Recife");
	});

	it("formata valores em reais", () => {
		expect(formatarCelulaResultado("receita_faturada", 35482.79)).toBe(
			"R$\u00a035.482,79",
		);
		expect(formatarCelulaResultado("valor_tributos", 1200)).toBe(
			"R$\u00a01.200,00",
		);
		expect(formatarCelulaResultado("receita_faturada", "16329205.90")).toBe(
			"R$\u00a016.329.205,90",
		);
		expect(formatarCelulaResultado("cod_uc", "0001")).toBe("0001");
	});

	it("formata pela unidade que o agente mandou, antes do nome da coluna", () => {
		expect(formatarCelulaResultado("receita_2024", 10, "R$")).toBe(
			"R$\u00a010,00",
		);
		expect(formatarCelulaResultado("percentual_tributos", 25, "%")).toBe("25%");
		expect(formatarCelulaResultado("total", "1200", "kWh")).toBe("1.200 kWh");
		expect(formatarCelulaResultado("n_ucs", 3, "contagem")).toBe("3");
		expect(formatarCelulaResultado("potencia", 4.5, "kWp")).toBe("4,5 kWp");
	});

	it("sem unidade, percentual vence o nome de dinheiro", () => {
		expect(formatarCelulaResultado("percentual_tributos", 25)).toBe("25%");
	});

	it("formata energia em kWh", () => {
		expect(formatarCelulaResultado("kwh_faturado", 1234.5)).toBe("1.235 kWh");
	});

	it("formata DEC, horas, FEC e satisfação", () => {
		expect(formatarCelulaResultado("dec", 1.254)).toBe("1,25 h");
		expect(formatarCelulaResultado("horas_interrompidas", 12)).toBe("12 h");
		expect(formatarCelulaResultado("fec", 0.347)).toBe("0,35");
		expect(formatarCelulaResultado("satisfacao_media", 4.25)).toBe("4,25");
	});

	it("formata percentual e número puro", () => {
		expect(formatarCelulaResultado("variacao_pct", 3.46)).toBe("3,5%");
		expect(formatarCelulaResultado("n_uc", 1234)).toBe("1.234");
	});
});

describe("sessaoDaApi", () => {
	it("cada registro da auditoria vira um turno respondido, na ordem", () => {
		const { session_id: _, ...registro } = resposta(
			"A receita foi de R$ 10,00.",
		);
		const sessao = sessaoDaApi(
			{
				session_id: "s1",
				titulo: "Receita de junho",
				favorita: true,
				criada_em: "2026-10-01T10:00:00Z",
				atualizada_em: "2026-10-01T10:05:00Z",
				turnos: [
					{
						...registro,
						audit_id: 7,
						pergunta: "Qual a receita?",
						criado_em: "2026-10-01T10:00:00Z",
					},
					{
						...registro,
						audit_id: 9,
						pergunta: "E em julho?",
						criado_em: "2026-10-01T10:05:00Z",
					},
				],
			},
			"henrique",
		);

		expect(sessao).toMatchObject({
			sessionId: "s1",
			usuarioLogin: "henrique",
			titulo: "Receita de junho",
			favorita: true,
			atualizadaEm: "2026-10-01T10:05:00Z",
		});
		expect(
			sessao.turnos.map((turno) => [turno.id, turno.question, turno.status]),
		).toEqual([
			["7", "Qual a receita?", "completed"],
			["9", "E em julho?", "completed"],
		]);
		expect(sessao.turnos[0].resposta).toMatchObject({
			session_id: "s1",
			answer: "A receita foi de R$ 10,00.",
		});
		expect(sessao.turnos[0].resposta).not.toHaveProperty("pergunta");
	});
});

function vazia(sessionId: string): SessaoConversa {
	return { ...sessao(sessionId), turnos: [] };
}

describe("mesclarSessoes", () => {
	it("mantém a versão local com mais turnos, para um follow-up não sumir", () => {
		const doServidor = sessao("s1");
		const local = {
			...sessao("s1"),
			turnos: [
				...sessao("s1").turnos,
				{ ...sessao("s1").turnos[0], id: "follow-up" },
			],
		};

		const [unica] = mesclarSessoes([local], [doServidor]);

		expect(unica.turnos.map((turno) => turno.id)).toEqual([
			"s1-turno",
			"follow-up",
		]);
	});

	it("mantém a conversa nova vazia em primeiro, antes das só locais e das salvas", () => {
		const resultado = mesclarSessoes(
			[vazia("nova"), sessao("local")],
			[sessao("s1")],
		);

		expect(resultado.map((item) => item.sessionId)).toEqual([
			"nova",
			"local",
			"s1",
		]);
	});

	it("guarda uma conversa vazia só, a primeira", () => {
		const resultado = mesclarSessoes([vazia("a"), vazia("b")], [sessao("s1")]);

		expect(resultado.map((item) => item.sessionId)).toEqual(["a", "s1"]);
	});

	it("fica com a do servidor quando ela tem mais turnos", () => {
		const doServidor = {
			...sessao("s1"),
			turnos: [
				...sessao("s1").turnos,
				{ ...sessao("s1").turnos[0], id: "outro" },
			],
		};

		expect(mesclarSessoes([sessao("s1")], [doServidor])[0]).toBe(doServidor);
	});
});

describe("desfazerAlteracao", () => {
	it("desfaz só o campo enviado, e só se a tela ainda mostra o valor enviado", () => {
		const tela = { ...sessao("s1", "Novo nome"), favorita: true };

		expect(
			desfazerAlteracao(tela, { titulo: "Novo nome" }, { titulo: "Antigo" }),
		).toMatchObject({ titulo: "Antigo", favorita: true });
		expect(
			desfazerAlteracao(
				tela,
				{ titulo: "Nome mais antigo" },
				{ titulo: "Antigo" },
			),
		).toMatchObject({ titulo: "Novo nome" });
	});
});

describe("reinserirSessao", () => {
	it("volta para a posição em que estava", () => {
		const lista = [sessao("a"), sessao("c")];

		expect(
			reinserirSessao(lista, sessao("b"), 1).map((item) => item.sessionId),
		).toEqual(["a", "b", "c"]);
	});

	it("nunca fica atrás de uma conversa vazia", () => {
		const lista = [vazia("nova")];

		expect(
			reinserirSessao(lista, sessao("b"), 3).map((item) => item.sessionId),
		).toEqual(["b", "nova"]);
	});
});

describe("formatarSessaoComoMarkdown", () => {
	it("exporta titulo, pergunta, resposta, tabela e SQL em markdown", () => {
		const md = formatarSessaoComoMarkdown({
			...sessao("md-1", "Receita de março"),
			turnos: [
				{
					id: "t1",
					question: "Qual foi a receita faturada em março de 2025?",
					criadoEm: "2026-10-01T10:00:00.000Z",
					status: "completed",
					resposta: {
						...resposta("A receita foi de R$ 16.329.205,90."),
						rows: [{ competencia: "2025-03", receita_faturada: 16329205.9 }],
						row_count: 1,
						sql: "SELECT receita_faturada FROM gold.sem_kpis_mensais",
					},
				},
			],
		});
		expect(md).toContain("# Receita de março");
		expect(md).toContain(
			"## Pergunta\n\nQual foi a receita faturada em março de 2025?",
		);
		expect(md).toContain("| competencia | receita_faturada |");
		expect(md).toContain(
			"```sql\nSELECT receita_faturada FROM gold.sem_kpis_mensais\n```",
		);
	});
});

describe("extrairMensagemErro", () => {
	it("explica a indisponibilidade do agente", () => {
		expect(extrairMensagemErro(new ApiError(503, null))).toBe(
			"O agente de IA não está disponível neste ambiente (verifique a configuração da chave do modelo).",
		);
	});

	it("explica a pergunta inválida", () => {
		expect(extrairMensagemErro(new ApiError(422, { detail: [] }))).toBe(
			"A pergunta enviada é inválida (máximo de 500 caracteres).",
		);
	});

	it("cai na mensagem genérica nos demais casos", () => {
		const generica =
			"Não foi possível concluir a consulta ao agente. Tente novamente.";
		expect(extrairMensagemErro(new ApiError(500, null))).toBe(generica);
		expect(extrairMensagemErro(new Error("boom"))).toBe(generica);
		expect(extrairMensagemErro("falhou")).toBe(generica);
	});
});
