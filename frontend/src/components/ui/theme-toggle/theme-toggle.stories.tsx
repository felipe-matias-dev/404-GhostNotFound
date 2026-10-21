import type { Meta, StoryObj } from "@storybook/react-vite";
import { Logo } from "#/components/layout/logo";
import { ThemeToggle } from "./theme-toggle";

// O toggle troca o tema do documento inteiro (atributo `data-tema` no <html>), então a
// story muda junto com ele.
const meta = {
	title: "Componentes/ThemeToggle",
	component: ThemeToggle,
	tags: ["autodocs"],
} satisfies Meta<typeof ThemeToggle>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};

export const NoCabecalho: Story = {
	render: () => (
		<header className="flex w-[32rem] items-center justify-between rounded-lg border border-border bg-bg p-4">
			<Logo />
			<ThemeToggle />
		</header>
	),
};
