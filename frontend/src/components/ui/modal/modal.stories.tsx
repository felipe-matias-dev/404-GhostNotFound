import type { Meta, StoryObj } from "@storybook/react-vite";
import { useRef, useState } from "react";
import { fn } from "storybook/test";
import { Button } from "#/components/ui/button";
import { HoldToConfirm } from "#/components/ui/hold-to-confirm";
import { Modal, type ModalProps } from "./modal";

const meta = {
	title: "Componentes/Modal",
	component: Modal,
	tags: ["autodocs"],
	args: {
		open: false,
		onClose: fn(),
		title: "Arquivar a carga de 03/2026?",
		description:
			"Ela sai dos painéis, mas continua no histórico e pode voltar a qualquer momento.",
	},
} satisfies Meta<typeof Modal>;

export default meta;
type Story = StoryObj<typeof meta>;

// O modal é controlado: a story guarda o `open` e abre por um botão, como a tela faz.
function ComGatilho({
	rotulo,
	...props
}: Omit<ModalProps, "open" | "onClose"> & {
	rotulo: string;
	onClose: () => void;
}) {
	const [aberto, setAberto] = useState(false);
	const fechar = () => {
		props.onClose();
		setAberto(false);
	};
	return (
		<>
			<Button variant="outline" onClick={() => setAberto(true)}>
				{rotulo}
			</Button>
			<Modal {...props} open={aberto} onClose={fechar} />
		</>
	);
}

export const Padrao: Story = {
	render: (args) => (
		<ComGatilho
			{...args}
			rotulo="Arquivar carga"
			footer={
				<>
					<Button variant="ghost">Voltar</Button>
					<Button>Arquivar</Button>
				</>
			}
		>
			<p className="text-text-muted">
				12 tabelas e 3 ajustes manuais estão nesta competência.
			</p>
		</ComGatilho>
	),
};

function Destrutivo(args: Story["args"]) {
	const voltar = useRef<HTMLButtonElement>(null);
	return (
		<ComGatilho
			{...(args as ModalProps)}
			rotulo="Excluir carga"
			title="Excluir a carga de 03/2026?"
			description="As 12 tabelas da competência saem junto. Não dá para desfazer."
			initialFocusRef={voltar}
			footer={
				<>
					<Button ref={voltar} variant="ghost">
						Voltar
					</Button>
					<HoldToConfirm
						tone="destructive"
						confirmLabel="Excluída"
						onConfirm={fn()}
					>
						Segure para excluir
					</HoldToConfirm>
				</>
			}
		/>
	);
}

// Ação irreversível: o foco abre na ação segura e a confirmação pede segurar.
export const AcaoDestrutiva: Story = {
	render: (args) => <Destrutivo {...args} />,
};

export const Carregando: Story = {
	render: (args) => (
		<ComGatilho
			{...args}
			rotulo="Salvando"
			closeOnEscape={false}
			closeOnBackdrop={false}
			footer={
				<>
					<Button variant="ghost" disabled>
						Voltar
					</Button>
					<Button disabled>Arquivando…</Button>
				</>
			}
		/>
	),
};

const ITENS = Array.from({ length: 14 }, (_, i) => i + 1);

export const ComRolagem: Story = {
	render: (args) => (
		<ComGatilho
			{...args}
			rotulo="Ver termos"
			title="Termos da carga"
			description={undefined}
			footer={<Button>Entendi</Button>}
		>
			<div className="flex flex-col gap-3 text-text-muted">
				{ITENS.map((item) => (
					<p key={item}>
						Item {item}: o corpo rola dentro do painel, e o cabeçalho e o rodapé
						ficam parados.
					</p>
				))}
			</div>
		</ComGatilho>
	),
};
