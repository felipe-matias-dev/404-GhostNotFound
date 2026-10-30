import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { Checkbox } from "./checkbox";

const meta = {
	title: "Componentes/Checkbox",
	component: Checkbox,
	tags: ["autodocs"],
	parameters: { layout: "centered" },
	args: {
		label: "Selecionar unidade consumidora",
		checked: false,
		onChange: () => {},
	},
	render: (args) => {
		const [checked, setChecked] = useState(args.checked);
		return <Checkbox {...args} checked={checked} onChange={setChecked} />;
	},
} satisfies Meta<typeof Checkbox>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};
export const Marcado: Story = { args: { checked: true } };
export const Parcial: Story = { args: { indeterminate: true } };
export const Desabilitado: Story = { args: { checked: true, disabled: true } };
