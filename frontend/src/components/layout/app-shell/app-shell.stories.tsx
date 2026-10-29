import { SignOutIcon } from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { NAVEGACAO, organizarNavegacao } from "#/components/layout/app-sidebar";
import { Pagina } from "#/components/layout/pagina";
import { Button } from "#/components/ui/button";
import { AppShell } from "./app-shell";

// Rota inicial do router de memória do Storybook em `parameters.rota`. Abaixo de 768px
// (viewport do Storybook) a sidebar vira o Sheet do trigger.
const meta = {
	title: "Layout/AppShell",
	component: AppShell,
	tags: ["autodocs"],
	parameters: { layout: "fullscreen", rota: "/receita" },
	args: {
		onConsultarUc: fn(),
		children: (
			<Pagina descricao="Ponte de receita entre dois períodos, separada em efeito preço, volume e mix." />
		),
	},
} satisfies Meta<typeof AppShell>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};

export const Atendimento: Story = {
	parameters: { rota: "/uc" },
	args: {
		itens: organizarNavegacao(NAVEGACAO, ["/uc"]),
		conta: (
			<div className="flex items-center gap-2 border-t border-border px-1 pt-3">
				<div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
					<p className="text-body font-medium">Camila</p>
					<p className="text-small text-text-muted">Atendimento</p>
				</div>
				<Button
					variant="ghost"
					size="icon-sm"
					aria-label="Sair do portal"
					onClick={fn()}
				>
					<SignOutIcon aria-hidden />
				</Button>
			</div>
		),
	},
};

export const ConteudoLongo: Story = {
	args: {
		children: (
			<Pagina descricao="O painel rola sozinho; sidebar e header ficam fixos.">
				{Array.from({ length: 30 }, (_, i) => (
					<div
						// biome-ignore lint/suspicious/noArrayIndexKey: linhas estáticas de exemplo.
						key={i}
						className="rounded-md border border-border-strong bg-surface-2 p-3 text-body"
					>
						Linha {i + 1}
					</div>
				))}
			</Pagina>
		),
	},
};

// Rota fora da navegação (ex.: página não encontrada): o Header fica sem título.
export const ForaDaNavegacao: Story = { parameters: { rota: "/inexistente" } };
