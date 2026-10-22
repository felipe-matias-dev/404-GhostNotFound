import {
	ArrowSquareOutIcon,
	BuildingsIcon,
	CalendarBlankIcon,
	CellSignalHighIcon,
	CircleHalfIcon,
	CircleNotchIcon,
	CurrencyCircleDollarIcon,
	GaugeIcon,
	XCircleIcon,
} from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { Badge } from "./badge";

const meta = {
	title: "Componentes/Badge",
	component: Badge,
	tags: ["autodocs"],
	args: { children: "Perdas técnicas" },
	argTypes: {
		variant: {
			control: "inline-radio",
			options: ["outline", "secondary", "ghost", "destructive", "link"],
		},
	},
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};

// Label: contorno + ponto colorido. A cor está no ponto; o texto fica neutro.
export const ComPonto: Story = {
	render: (args) => (
		<div className="flex flex-wrap gap-2">
			<Badge {...args}>
				<span
					data-icon="inline-start"
					aria-hidden
					className="size-1.5 rounded-full bg-info"
				/>
				Perdas técnicas
			</Badge>
			<Badge {...args}>
				<span
					data-icon="inline-start"
					aria-hidden
					className="size-1.5 rounded-full bg-accent"
				/>
				Revisão
			</Badge>
			<Badge {...args}>
				<span
					data-icon="inline-start"
					aria-hidden
					className="size-1.5 rounded-full bg-success"
				/>
				Sincronizado
			</Badge>
		</div>
	),
};

// Iniciativa: pílula preenchida com ícone colorido.
export const Preenchido: Story = {
	args: { variant: "secondary" },
	render: (args) => (
		<div className="flex flex-wrap gap-2">
			<Badge {...args}>
				<CurrencyCircleDollarIcon
					data-icon="inline-start"
					aria-hidden
					className="text-warning"
				/>
				Receita
			</Badge>
			<Badge {...args}>
				<GaugeIcon data-icon="inline-start" aria-hidden className="text-info" />
				Operação 2026
			</Badge>
		</div>
	),
};

// Propriedades: sem contorno nem fundo, ícone + valor (linha de metadados).
export const Propriedades: Story = {
	args: { variant: "ghost" },
	render: (args) => (
		<div className="flex flex-wrap items-center gap-1">
			<Badge {...args}>
				<CircleHalfIcon
					data-icon="inline-start"
					aria-hidden
					weight="fill"
					className="text-accent-text"
				/>
				Em inspeção
			</Badge>
			<Badge {...args}>
				<CellSignalHighIcon data-icon="inline-start" aria-hidden />
				Alta
			</Badge>
			<Badge {...args}>
				<CalendarBlankIcon data-icon="inline-start" aria-hidden />
				mar/2026
			</Badge>
			<Badge {...args}>
				<BuildingsIcon data-icon="inline-start" aria-hidden />
				UC 0042
			</Badge>
		</div>
	),
};

export const Destrutivo: Story = {
	args: { variant: "destructive" },
	render: (args) => (
		<Badge {...args}>
			<XCircleIcon data-icon="inline-start" aria-hidden />
			Falhou
		</Badge>
	),
};

export const Carregando: Story = {
	render: (args) => (
		<Badge {...args}>
			<CircleNotchIcon
				data-icon="inline-start"
				aria-hidden
				className="animate-spin motion-reduce:animate-none"
			/>
			Sincronizando
		</Badge>
	),
};

// Badge como link: o elemento vem do `render`.
export const ComoLink: Story = {
	render: (args) => (
		<Badge {...args} render={(props) => <a href="#uc-0042" {...props} />}>
			UC 0042
			<ArrowSquareOutIcon data-icon="inline-end" aria-hidden />
		</Badge>
	),
};
