import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "./button";

const meta = {
	title: "Componentes/Button",
	component: Button,
	tags: ["autodocs"],
	args: { children: "Salvar" },
	argTypes: {
		variant: {
			control: "select",
			options: [
				"default",
				"destructive",
				"outline",
				"secondary",
				"ghost",
				"link",
			],
		},
		size: {
			control: "select",
			options: ["xs", "sm", "default", "lg"],
		},
	},
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

const variantes = [
	"default",
	"destructive",
	"outline",
	"secondary",
	"ghost",
	"link",
] as const;

export const Padrao: Story = {};

export const Variantes: Story = {
	render: (args) => (
		<div className="flex flex-wrap items-center gap-3">
			{variantes.map((variant) => (
				<Button key={variant} {...args} variant={variant}>
					{variant}
				</Button>
			))}
		</div>
	),
};

export const Tamanhos: Story = {
	render: (args) => (
		<div className="flex items-center gap-3">
			<Button {...args} size="xs">
				Extra pequeno
			</Button>
			<Button {...args} size="sm">
				Pequeno
			</Button>
			<Button {...args}>Padrão</Button>
			<Button {...args} size="lg">
				Grande
			</Button>
		</div>
	),
};

export const Desabilitado: Story = {
	render: (args) => (
		<div className="flex flex-wrap items-center gap-3">
			{variantes.map((variant) => (
				<Button key={variant} {...args} variant={variant} disabled>
					{variant}
				</Button>
			))}
		</div>
	),
};

export const Carregando: Story = {
	args: { children: "Salvando…", disabled: true, "aria-busy": true },
};

export const ComoLink: Story = {
	args: { asChild: true, variant: "outline" },
	render: (args) => (
		<Button {...args}>
			<a href="#relatorio">Abrir relatório</a>
		</Button>
	),
};

export const Claro: Story = {
	...Variantes,
	decorators: [
		(Story) => (
			<div data-tema="claro" className="rounded-lg bg-bg p-6 text-text">
				<Story />
			</div>
		),
	],
};
