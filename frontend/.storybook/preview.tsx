import type { Preview } from "@storybook/react-vite";
import {
	createMemoryHistory,
	createRootRoute,
	createRoute,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { useEffect } from "storybook/preview-api";
import { themes } from "storybook/theming";
import "../src/styles.css";

// Componentes com Link (sidebar, app-shell) precisam de um router. A story declara a rota
// atual em `parameters.rota`; o splat aceita qualquer caminho sem cair no "não encontrado".
function criarRouter(Story: () => React.ReactNode, rota: string) {
	const raiz = createRootRoute({ component: Story });
	const qualquer = createRoute({ getParentRoute: () => raiz, path: "$" });
	return createRouter({
		routeTree: raiz.addChildren([qualquer]),
		history: createMemoryHistory({ initialEntries: [rota] }),
	});
}

const preview: Preview = {
	parameters: {
		layout: "centered",
		controls: { expanded: true },
		// Páginas de docs no escuro, o tema principal da marca (o padrão do Storybook é claro e
		// deixava texto claro sobre fundo branco).
		docs: { theme: themes.dark },
		// Violações de acessibilidade aparecem no painel "Accessibility" de cada story.
		a11y: { test: "todo" },
		options: {
			storySort: {
				order: ["Introdução", "Fundamentos", "Componentes", "Layout"],
			},
		},
	},
	// Seletor "Tema" na barra do Storybook: aplica o tema como o app faz.
	globalTypes: {
		tema: {
			description: "Tema da interface",
			toolbar: {
				title: "Tema",
				icon: "contrast",
				items: [
					{ value: "escuro", title: "Escuro", icon: "moon" },
					{ value: "claro", title: "Claro", icon: "sun" },
				],
				dynamicTitle: true,
			},
		},
	},
	initialGlobals: { tema: "escuro" },
	decorators: [
		(Story, { parameters }) => {
			const rota = parameters.rota as string | undefined;
			if (!rota) return <Story />;
			return <RouterProvider router={criarRouter(Story, rota)} />;
		},
		(Story, { globals, viewMode }) => {
			const claro = globals.tema === "claro";

			// Canvas: o tema vai no <html>, como no app. Em docs o <html> fica no escuro.
			const htmlClaro = claro && viewMode !== "docs";
			useEffect(() => {
				const raiz = document.documentElement;
				if (htmlClaro) raiz.dataset.tema = "claro";
				else delete raiz.dataset.tema;
			}, [htmlClaro]);
			// Docs: várias stories (e as páginas de Fundamentos, com os dois temas lado a lado)
			// dividem o mesmo <html>, que fica no escuro; cada story ganha o próprio fundo do tema.
			if (viewMode === "docs") {
				return (
					<div
						data-tema={claro ? "claro" : undefined}
						className="rounded-lg bg-bg p-6 text-text"
					>
						<Story />
					</div>
				);
			}
			return <Story />;
		},
	],
};

export default preview;
