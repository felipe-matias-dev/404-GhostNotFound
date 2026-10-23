import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import {
	FloatingLabelInput,
	type FloatingLabelInputProps,
	FloatingLabelTextarea,
} from "./floating-label";

const meta = {
	title: "Componentes/FloatingLabel",
	component: FloatingLabelInput,
	tags: ["autodocs"],
	args: { label: "Código da UC", hint: "Como aparece na fatura." },
	decorators: [
		(Story) => (
			<div className="w-80">
				<Story />
			</div>
		),
	],
} satisfies Meta<typeof FloatingLabelInput>;

export default meta;
type Story = StoryObj<typeof meta>;

// Controlado, como nas telas: o rótulo sobe no foco e fica em cima enquanto há texto.
function Controlado(props: FloatingLabelInputProps) {
	const [valor, setValor] = useState(props.defaultValue ?? "");
	return (
		<FloatingLabelInput
			{...props}
			defaultValue={undefined}
			value={valor}
			onChange={setValor}
		/>
	);
}

export const Padrao: Story = { render: (args) => <Controlado {...args} /> };

// Valor já preenchido: o rótulo começa em cima, sem animar ao carregar.
export const Preenchido: Story = {
	args: { defaultValue: "0044" },
	render: (args) => <Controlado {...args} />,
};

export const ComContador: Story = {
	args: {
		label: "Referência",
		maxLength: 16,
		hint: "Sai no cabeçalho do laudo.",
	},
	render: (args) => <Controlado {...args} />,
};

export const Invalido: Story = {
	args: {
		defaultValue: "44",
		invalid: true,
		hint: "O código tem 4 dígitos.",
		required: true,
	},
	render: (args) => <Controlado {...args} />,
};

export const Desabilitado: Story = {
	args: { defaultValue: "0044", disabled: true },
	render: (args) => <Controlado {...args} />,
};

function AreaDeTexto() {
	const [valor, setValor] = useState("");
	return (
		<FloatingLabelTextarea
			label="Observação (opcional)"
			value={valor}
			onChange={setValor}
			maxLength={1000}
			rows={4}
		/>
	);
}

// Várias linhas: o rótulo repousa na primeira linha e sobe igual ao do input.
export const Textarea: Story = { render: () => <AreaDeTexto /> };
