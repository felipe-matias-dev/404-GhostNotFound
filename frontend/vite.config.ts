import babel from "@rolldown/plugin-babel";
import tailwindcss from "@tailwindcss/vite";
import { devtools } from "@tanstack/devtools-vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact, { reactCompilerPreset } from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

const config = defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd(), "");

	return {
		resolve: { tsconfigPaths: true },
		server: {
			proxy: {
				// Dev: /api/* → FastAPI, sem o prefixo /api (ex.: /api/ucs → <alvo>/ucs).
				"/api": {
					target: env.API_PROXY_TARGET || "http://localhost:8000",
					changeOrigin: true,
					rewrite: (path) => path.replace(/^\/api/, ""),
				},
			},
		},
		plugins: [
			devtools(),
			tailwindcss(),
			// SPA: sem SSR; o FastAPI é o único backend.
			tanstackStart({ spa: { enabled: true } }),
			viteReact(),
			babel({ presets: [reactCompilerPreset()] }),
		],
	};
});

export default config;
