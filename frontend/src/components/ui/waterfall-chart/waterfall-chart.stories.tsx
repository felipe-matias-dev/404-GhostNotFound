import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { Button } from "#/components/ui/button";
import { formatKWh } from "#/lib/format";
import { WaterfallChart, type WaterfallStep } from "./waterfall-chart";

const QUEDA: WaterfallStep[] = [
	{ id: "base", label: "Receita base", value: 48_215_330.12, kind: "total" },
	{ id: "tarifa", label: "Preço · tarifa", value: 1_204_118.4, kind: "delta" },
	{
		id: "bandeira",
		label: "Preço · bandeira",
		value: -1_538_902.77,
		kind: "delta",
	},
	{ id: "volume", label: "Volume", value: -2_310_455.08, kind: "delta" },
	{ id: "mix", label: "Mix", value: 142_310.5, kind: "delta" },
	{ id: "atual", label: "Receita atual", value: 45_712_401.17, kind: "total" },
];

const ALTA: WaterfallStep[] = [
	{ id: "base", label: "Receita base", value: 3_120_400, kind: "total" },
	{ id: "tarifa", label: "Preço · tarifa", value: 210_330, kind: "delta" },
	{ id: "bandeira", label: "Preço · bandeira", value: 96_120, kind: "delta" },
	{ id: "volume", label: "Volume", value: 41_870, kind: "delta" },
	{ id: "mix", label: "Mix", value: 0, kind: "delta" },
	{ id: "atual", label: "Receita atual", value: 3_468_720, kind: "total" },
];

const meta = {
	title: "Componentes/WaterfallChart",
	component: WaterfallChart,
	tags: ["autodocs"],
	parameters: { layout: "padded" },
	args: {
		label: "Ponte de receita da empresa",
		steps: QUEDA,
		compareLabel: "vs. receita base",
		percentLabel: "Sobre a receita base",
		summary: (
			<>
				A receita{" "}
				<span className="font-medium text-text">caiu R$ 2.502.928,95</span>{" "}
				(-5,2%) de jan–dez 2024 para jan–dez 2025.
			</>
		),
	},
	decorators: [
		(Story) => (
			<div className="mx-auto w-full max-w-3xl">
				<Story />
			</div>
		),
	],
} satisfies Meta<typeof WaterfallChart>;

export default meta;
type Story = StoryObj<typeof meta>;

// Totais longe do zero: o eixo começa perto do menor acumulado, com corte nas barras de total.
export const Padrao: Story = {};

export const Alta: Story = {
	args: {
		label: "Ponte de receita de Olinda",
		steps: ALTA,
		summary: "A receita de Olinda subiu R$ 348.320,00 (+11,2%).",
	},
};

// Ação ao lado da frase de leitura; no app, o botão do insight de IA da tela.
export const ComAcao: Story = {
	args: {
		summaryAction: (
			<Button variant="outline" size="xs">
				Insight feito por IA
			</Button>
		),
	},
};

// Container estreito (coluna ao lado do mapa, celular): a coluna de percentual sai.
export const Estreito: Story = {
	decorators: [
		(Story) => (
			<div className="w-80">
				<Story />
			</div>
		),
	],
};

export const OutraUnidade: Story = {
	args: {
		label: "Ponte de energia faturada",
		compareLabel: "vs. consumo base",
		percentLabel: "Sobre o consumo base",
		formatValue: formatKWh,
		summary: undefined,
		steps: [
			{ id: "base", label: "Consumo base", value: 812_400, kind: "total" },
			{ id: "gd", label: "Geração própria", value: -64_210, kind: "delta" },
			{ id: "novas", label: "Novas ligações", value: 18_930, kind: "delta" },
			{ id: "atual", label: "Consumo atual", value: 767_120, kind: "total" },
		],
	},
};

// Troca de recorte: as barras deslizam até a nova posição.
export const TrocaDeDados: Story = {
	render: (args) => {
		const [alta, setAlta] = useState(false);
		return (
			<div className="flex flex-col items-start gap-3">
				<Button variant="outline" size="sm" onClick={() => setAlta((v) => !v)}>
					Trocar recorte
				</Button>
				<WaterfallChart
					{...args}
					summary={undefined}
					steps={alta ? ALTA : QUEDA}
					className="w-full"
				/>
			</div>
		);
	},
};

// Efeitos clicáveis: clicar marca o efeito; clicar de novo desmarca.
export const Selecionavel: Story = {
	render: (args) => {
		const [marcado, setMarcado] = useState<string | null>("volume");
		return (
			<WaterfallChart
				{...args}
				selectedId={marcado}
				onSelect={(step) =>
					setMarcado((atual) => (atual === step.id ? null : step.id))
				}
			/>
		);
	},
};

export const Carregando: Story = { args: { steps: undefined, loading: true } };

export const Erro: Story = {
	args: {
		steps: undefined,
		error: "Não foi possível carregar a ponte de receita.",
		onRetry: () => {},
	},
};

export const Vazio: Story = {
	args: {
		steps: [],
		summary: undefined,
		emptyMessage: "Sem decomposição de receita para este recorte.",
	},
};
