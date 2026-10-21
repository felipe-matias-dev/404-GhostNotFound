import type { Preview } from "@storybook/react-vite";
import { useEffect } from "storybook/preview-api";
import "../src/styles.css";

const preview: Preview = {
	parameters: {
		layout: "centered",
		controls: { expanded: true },
		// Violações de acessibilidade aparecem no painel "Accessibility" de cada story.
		a11y: { test: "todo" },
		options: {
			storySort: {
				order: ["Introdução", "Fundamentos", "Componentes", "Layout"],
			},
		},
	},
	// Seletor "Tema" na barra do Storybook: aplica o tema no <html>, como o app faz.
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
		(Story, { globals, viewMode }) => {
			// Só no canvas: as páginas de docs mostram os dois temas lado a lado e dependem do
			// <html> no escuro.
			const tema = viewMode === "docs" ? "escuro" : globals.tema;
			useEffect(() => {
				const raiz = document.documentElement;
				if (tema === "claro") raiz.dataset.tema = "claro";
				else delete raiz.dataset.tema;
			}, [tema]);
			return Story();
		},
	],
};

export default preview;
