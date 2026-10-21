import type { Meta, StoryObj } from "@storybook/react-vite";
import { Logo } from "./logo";

const meta = {
	title: "Layout/Logo",
	component: Logo,
	tags: ["autodocs"],
	args: { className: "bg-bg p-6" },
} satisfies Meta<typeof Logo>;

export default meta;
type Story = StoryObj<typeof meta>;

// Tema claro: seletor "Tema" na barra do Storybook.
export const Padrao: Story = {};
