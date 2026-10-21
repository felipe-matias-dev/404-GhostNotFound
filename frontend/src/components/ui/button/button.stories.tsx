import {
	CircleNotchIcon,
	DownloadSimpleIcon,
	PlusIcon,
	TrashIcon,
} from "@phosphor-icons/react";
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
	args: {
		disabled: true,
		"aria-busy": true,
		children: (
			<>
				<CircleNotchIcon
					aria-hidden
					className="animate-spin motion-reduce:animate-none"
				/>
				Salvando…
			</>
		),
	},
};

// Ícone à esquerda do texto: o Button já dimensiona em 16px e ajusta o padding.
export const ComIcone: Story = {
	render: (args) => (
		<div className="flex flex-wrap items-center gap-3">
			<Button {...args}>
				<PlusIcon aria-hidden />
				Nova inspeção
			</Button>
			<Button {...args} variant="outline">
				<DownloadSimpleIcon aria-hidden />
				Exportar CSV
			</Button>
			<Button {...args} variant="destructive">
				<TrashIcon aria-hidden />
				Excluir
			</Button>
		</div>
	),
};

// Só ícone: o nome acessível vem do aria-label do botão.
export const SoIcone: Story = {
	render: (args) => (
		<div className="flex items-center gap-3">
			<Button
				{...args}
				size="icon-sm"
				variant="ghost"
				aria-label="Exportar CSV"
			>
				<DownloadSimpleIcon aria-hidden />
			</Button>
			<Button
				{...args}
				size="icon"
				variant="outline"
				aria-label="Nova inspeção"
			>
				<PlusIcon aria-hidden />
			</Button>
			<Button {...args} size="icon-lg" aria-label="Nova inspeção">
				<PlusIcon aria-hidden />
			</Button>
		</div>
	),
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
