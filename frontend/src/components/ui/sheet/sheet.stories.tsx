import { ListIcon } from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "#/components/ui/button";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetFooter,
	SheetHeader,
	SheetTitle,
	SheetTrigger,
} from "./sheet";

const meta = {
	title: "Componentes/Sheet",
	component: Sheet,
	tags: ["autodocs"],
} satisfies Meta<typeof Sheet>;

export default meta;
type Story = StoryObj<typeof meta>;

function Exemplo({
	side,
	aberto = false,
}: {
	side: "top" | "right" | "bottom" | "left";
	aberto?: boolean;
}) {
	return (
		<Sheet defaultOpen={aberto}>
			<SheetTrigger render={<Button variant="outline" />}>
				<ListIcon aria-hidden />
				Abrir painel
			</SheetTrigger>
			<SheetContent side={side}>
				<SheetHeader>
					<SheetTitle>Filtros</SheetTitle>
					<SheetDescription>
						Período, município e classe de consumo.
					</SheetDescription>
				</SheetHeader>
				<SheetFooter>
					<Button>Aplicar</Button>
				</SheetFooter>
			</SheetContent>
		</Sheet>
	);
}

export const Padrao: Story = { render: () => <Exemplo side="right" /> };

// Navegação do app em telas menores que `lg` (ver Layout/AppShell).
export const Esquerda: Story = { render: () => <Exemplo side="left" /> };

export const Aberto: Story = {
	parameters: { layout: "fullscreen" },
	render: () => <Exemplo side="right" aberto />,
};
