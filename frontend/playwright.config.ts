import { defineConfig } from "@playwright/test";

// Os testes de agente chamam o modelo de verdade e batem na cota do dia: por isso rodam um por
// vez, fora do CI, contra o stack já de pé (make e2e-agente).
export default defineConfig({
	testDir: "./e2e",
	timeout: 180_000,
	workers: 1,
	reporter: [["list"]],
	use: {
		baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
		trace: "retain-on-failure",
		screenshot: "only-on-failure",
	},
});
