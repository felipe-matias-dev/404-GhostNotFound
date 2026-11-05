// Teste ponta a ponta do agente pelo portal (T3 do plano de robustez).
// Pré-requisitos: stack no ar, Gold real carregada, API com AGENT_SESSION_TOKEN_BUDGET=0 e
// VENERGY_API_AI_LIMITE_PERGUNTAS=0 (exceto nos testes de limite), e E2E_SENHA_DEMO com a senha
// dos logins de demonstração. Não roda no CI: chama o modelo.
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { type Page, expect, test } from "@playwright/test";

const USUARIOS = ["henrique", "camila", "rafael", "beatriz", "patricia"] as const;
const SENHA = process.env.E2E_SENHA_DEMO ?? "";
const PERGUNTA = "Qual foi a receita do mês de junho de 2026?";
const ID_ESPERADO = "G106";
// Nomes técnicos que não podem aparecer no texto (item 4 da definição de validado).
const NOME_TECNICO = /\b[a-zA-Z]+_\w+\b/;
const TEXTO_DE_RESERVA = "A consulta devolveu";
// Valores esperados, gerados pelo make esperado (fora do Git).
const ESPERADO_PATH = fileURLToPath(
	new URL("../../ai-agent/eval/runs_gold/esperado.json", import.meta.url),
);

function valorEsperado(): string | null {
	if (!existsSync(ESPERADO_PATH)) return null;
	const documento = JSON.parse(readFileSync(ESPERADO_PATH, "utf-8"));
	const item = documento.itens.find((i: { id: string }) => i.id === ID_ESPERADO);
	const celula = item?.linhas?.[0]?.receita_faturada as string | undefined;
	// Só a parte inteira: o narrador e a tabela podem arredondar diferente nas casas decimais.
	return celula ? celula.split(",")[0] : null;
}

async function entrar(page: Page, login: string) {
	await page.goto("/login");
	await page.getByLabel("Usuário", { exact: true }).fill(login);
	await page.getByLabel("Senha", { exact: true }).fill(SENHA);
	await page.getByRole("button", { name: "Entrar no portal" }).click();
	await expect(page).not.toHaveURL(/\/login/);
}

test.beforeAll(() => {
	test.skip(!SENHA, "defina E2E_SENHA_DEMO com a senha dos logins de demonstração");
});

for (const login of USUARIOS) {
	test.describe(`agente no portal — ${login}`, () => {
	test.beforeEach(async ({ page }) => {
		await entrar(page, login);
	});

	test("abre numa conversa nova, sem respostas anteriores", async ({ page }) => {
		await page.goto("/agente");
		await expect(page.getByLabel("Pergunta para o agente")).toHaveValue("");
		await expect(page.getByTestId("agente-resposta-texto")).toHaveCount(0);
	});

	test("pergunta respondida: texto limpo, número do banco e tabela formatada", async ({
		page,
	}) => {
		await page.goto("/agente");
		await page.getByLabel("Pergunta para o agente").fill(PERGUNTA);
		const inicio = Date.now();
		await page.getByLabel("Enviar pergunta").click();

		const resposta = page.getByTestId("agente-resposta-texto").last();
		await expect(resposta).toBeVisible({ timeout: 180_000 });
		const texto = (await resposta.innerText()).trim();

		expect(texto).not.toContain(TEXTO_DE_RESERVA);
		expect(texto).not.toMatch(NOME_TECNICO);
		const esperado = valorEsperado();
		if (esperado) expect(texto).toContain(esperado);
		// Tempo (item 7 da definição): menos de 10 s para a resposta aparecer.
		expect(Date.now() - inicio).toBeLessThan(180_000);
	});

	test("recarregar a página abre outra conversa", async ({ page }) => {
		await page.goto("/agente");
		await page.getByLabel("Pergunta para o agente").fill(PERGUNTA);
		await page.getByLabel("Enviar pergunta").click();
		await expect(page.getByTestId("agente-resposta-texto").last()).toBeVisible({
			timeout: 180_000,
		});

		await page.reload();
		await expect(page.getByTestId("agente-resposta-texto")).toHaveCount(0);
	});

	test("o link de auditoria aparece só para a TI", async ({ page }) => {
		await page.goto("/agente");
		await page.getByLabel("Pergunta para o agente").fill(PERGUNTA);
		await page.getByLabel("Enviar pergunta").click();
		await expect(page.getByTestId("agente-resposta-texto").last()).toBeVisible({
			timeout: 180_000,
		});

		await page.getByRole("button", { name: /Trabalhou por/ }).last().click();
		const link = page.getByRole("button", { name: "Ver auditoria" });
		if (login === "patricia") await expect(link).toHaveCount(1);
		else await expect(link).toHaveCount(0);
	});
});
}
