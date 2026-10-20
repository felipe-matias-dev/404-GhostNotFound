import type { Preview } from "@storybook/react-vite";
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
};

export default preview;
