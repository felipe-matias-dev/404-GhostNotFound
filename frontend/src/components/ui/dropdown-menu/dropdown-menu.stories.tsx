import { CaretDownIcon } from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { buttonVariants } from "#/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "./dropdown-menu";

const MUNICIPIOS = [
	"Cabo de Santo Agostinho",
	"Jaboatão dos Guararapes",
	"Olinda",
	"Paulista",
	"Recife",
];

const meta = {
	title: "Componentes/DropdownMenu",
	component: DropdownMenu,
	tags: ["autodocs"],
} satisfies Meta<typeof DropdownMenu>;

export default meta;
type Story = StoryObj<typeof meta>;

// Escolha única (rádio): o item marcado mostra o check.
export const Padrao: Story = {
	render: function Render() {
		const [valor, setValor] = useState("Recife");
		return (
			<DropdownMenu>
				<DropdownMenuTrigger
					className={buttonVariants({ variant: "outline", size: "sm" })}
				>
					{valor || "Todos os municípios"}
					<CaretDownIcon aria-hidden />
				</DropdownMenuTrigger>
				<DropdownMenuContent>
					<DropdownMenuRadioGroup value={valor} onValueChange={setValor}>
						<DropdownMenuRadioItem value="">
							Todos os municípios
						</DropdownMenuRadioItem>
						<DropdownMenuSeparator />
						<DropdownMenuGroup>
							<DropdownMenuLabel>Municípios</DropdownMenuLabel>
							{MUNICIPIOS.map((m) => (
								<DropdownMenuRadioItem key={m} value={m}>
									{m}
								</DropdownMenuRadioItem>
							))}
						</DropdownMenuGroup>
					</DropdownMenuRadioGroup>
				</DropdownMenuContent>
			</DropdownMenu>
		);
	},
};

export const Acoes: Story = {
	render: () => (
		<DropdownMenu defaultOpen>
			<DropdownMenuTrigger
				className={buttonVariants({ variant: "outline", size: "sm" })}
			>
				Ações
				<CaretDownIcon aria-hidden />
			</DropdownMenuTrigger>
			<DropdownMenuContent>
				<DropdownMenuItem>Exportar CSV</DropdownMenuItem>
				<DropdownMenuItem>Copiar link do recorte</DropdownMenuItem>
				<DropdownMenuSeparator />
				<DropdownMenuItem disabled>Gerar OIs (sem seleção)</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenu>
	),
};

export const Carregando: Story = {
	render: () => (
		<DropdownMenu defaultOpen>
			<DropdownMenuTrigger
				className={buttonVariants({ variant: "outline", size: "sm" })}
			>
				Todos os bairros
				<CaretDownIcon aria-hidden />
			</DropdownMenuTrigger>
			<DropdownMenuContent>
				<DropdownMenuRadioGroup value="">
					<DropdownMenuRadioItem value="">
						Todos os bairros
					</DropdownMenuRadioItem>
					<DropdownMenuSeparator />
					<DropdownMenuGroup>
						<DropdownMenuLabel>Carregando…</DropdownMenuLabel>
					</DropdownMenuGroup>
				</DropdownMenuRadioGroup>
			</DropdownMenuContent>
		</DropdownMenu>
	),
};
