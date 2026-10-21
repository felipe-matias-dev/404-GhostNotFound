import { ArrowsClockwiseIcon } from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useEffect, useState } from "react";
import { Button } from "#/components/ui/button";
import { formatBRL } from "#/lib/format";
import { SkeletonSwap } from "./skeleton-swap";

const TEXTO =
	"Receita faturada da competência com 12 unidades consumidoras conferidas. As perdas não técnicas caíram pelo terceiro mês seguido.";

const meta = {
	title: "Componentes/SkeletonSwap",
	component: SkeletonSwap,
	tags: ["autodocs"],
	args: {
		ready: true,
		lines: 3,
		label: "Resumo",
		children: <p className="text-body text-text-muted">{TEXTO}</p>,
	},
	decorators: [
		(Story) => (
			<div className="w-96 rounded-lg border border-border bg-surface-1 p-4">
				<h3 className="mb-2 text-heading">Resumo de 03/2026</h3>
				<Story />
			</div>
		),
	],
} satisfies Meta<typeof SkeletonSwap>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};

export const Carregando: Story = { args: { ready: false } };

// Simula a requisição: 1,2 s carregando, depois troca para o conteúdo sem mexer na altura.
export const Troca: Story = {
	render: function Render(args) {
		const [ready, setReady] = useState(false);
		const [rodada, setRodada] = useState(0);

		// biome-ignore lint/correctness/useExhaustiveDependencies: `rodada` dispara uma nova carga.
		useEffect(() => {
			setReady(false);
			const t = setTimeout(() => setReady(true), 1200);
			return () => clearTimeout(t);
		}, [rodada]);

		return (
			<>
				<SkeletonSwap {...args} ready={ready} />
				<Button
					variant="ghost"
					size="sm"
					className="mt-3"
					onClick={() => setRodada((r) => r + 1)}
				>
					<ArrowsClockwiseIcon aria-hidden />
					Recarregar
				</Button>
			</>
		);
	},
};

// Skeleton com a forma do conteúdo (KPI): `reserve` fixa a altura e `skeleton` desenha o molde.
export const FormaPropria: Story = {
	args: {
		ready: false,
		label: "Receita",
		reserve: 44,
		skeleton: <div className="h-10 w-48 rounded-md bg-pressed" />,
		children: (
			<p className="font-display text-metric tabular-nums">
				{formatBRL(1250000)}
			</p>
		),
	},
};
