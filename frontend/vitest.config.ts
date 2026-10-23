import { defineConfig } from "vitest/config";

// Só funções puras (conversões, regras de tela); sem DOM. Separado do vite.config.ts para não
// carregar os plugins do TanStack Start.
export default defineConfig({
	resolve: { tsconfigPaths: true },
	test: { include: ["src/**/__tests__/**/*.test.ts"] },
});
