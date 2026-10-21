import type { StorybookConfig } from "@storybook/react-vite";
import remarkGfm from "remark-gfm";
import type { PluginOption } from "vite";

// Plugins do TanStack Start, Router e devtools montam o app inteiro (entrada própria,
// manifest, rotas) e quebram o build do Storybook.
function semTanstack(plugins: PluginOption[]): PluginOption[] {
	return plugins
		.filter(
			(plugin) =>
				!(plugin && "name" in plugin && /^@?tanstack/.test(plugin.name)),
		)
		.map((plugin) => (Array.isArray(plugin) ? semTanstack(plugin) : plugin));
}

const config: StorybookConfig = {
	framework: "@storybook/react-vite",
	stories: ["./docs/**/*.mdx", "../src/**/*.stories.tsx"],
	addons: [
		// remark-gfm: tabelas Markdown nas páginas de Fundamentos.
		{
			name: "@storybook/addon-docs",
			options: {
				mdxPluginOptions: { mdxCompileOptions: { remarkPlugins: [remarkGfm] } },
			},
		},
		"@storybook/addon-a11y",
	],
	core: { disableTelemetry: true },
	// Reaproveita o vite.config.ts (Tailwind, React Compiler, alias #/) sem o TanStack.
	viteFinal: (viteConfig) => {
		viteConfig.plugins = semTanstack(viteConfig.plugins ?? []);
		return viteConfig;
	},
};

export default config;
