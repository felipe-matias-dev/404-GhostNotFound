import type { Meta, StoryObj } from "@storybook/react-vite";
import { Sparkline } from "./sparkline";

const doisAnos = [
	42.1, 43.4, 41.2, 39.0, 37.5, 35.2, 34.8, 36.1, 38.4, 40.9, 41.7, 42.2, 45.1,
	46.3, 46.0, 41.4, 40.6, 40.0, 41.1, 40.1, 40.7, 41.6, 43.5, 44.2,
];

const meta = {
	title: "Componentes/Sparkline",
	component: Sparkline,
	tags: ["autodocs"],
	args: { values: doisAnos, highlight: 23, reference: 11 },
	decorators: [
		(Story) => (
			<div className="w-48 rounded-md border border-border bg-surface-1 p-4">
				<Story />
			</div>
		),
	],
} satisfies Meta<typeof Sparkline>;

export default meta;
type Story = StoryObj<typeof meta>;

// O mês atual em `chart-1`; o mês base, um anel neutro.
export const Padrao: Story = {};

// Sem ponto marcado: só a forma.
export const SoALinha: Story = {
	args: { highlight: undefined, reference: undefined },
};

// Mês sem dado interrompe a linha; o ponto de um mês vazio não aparece.
export const ComBuraco: Story = {
	args: {
		values: doisAnos.map((v, i) => (i >= 5 && i <= 8 ? null : v)),
		reference: 6,
	},
};

// Série constante: linha no meio, sem dividir por zero.
export const Constante: Story = {
	args: { values: Array.from({ length: 12 }, () => 2), highlight: 11 },
};

// Menos de dois valores: não há forma, e nada é desenhado.
export const Vazio: Story = {
	args: { values: [null, null, 4.1], highlight: 2 },
};
