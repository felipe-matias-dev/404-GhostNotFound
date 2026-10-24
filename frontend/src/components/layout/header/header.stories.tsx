import { CaretDownIcon, SidebarIcon } from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbList,
	BreadcrumbSeparator,
} from "#/components/ui/breadcrumb";
import { Button } from "#/components/ui/button";
import { ThemeToggle } from "#/components/ui/theme-toggle";
import { Header } from "./header";
import { HeaderTrilha, HeaderTrilhaContext } from "./header-trilha";

const meta = {
	title: "Layout/Header",
	component: Header,
	tags: ["autodocs"],
	args: {
		titulo: "Receita",
		acoes: <ThemeToggle className="size-7" />,
		className: "w-[40rem] bg-surface-1",
	},
} satisfies Meta<typeof Header>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};

// No app, `inicio` recebe o GatilhoNavegacao quando a navegação está recolhida (no celular abre o Sheet).
export const ComMenu: Story = {
	args: {
		className: "w-96 bg-surface-1",
		inicio: (
			<Button variant="ghost" size="icon-sm" aria-label="Recolher navegação">
				<SidebarIcon aria-hidden />
			</Button>
		),
	},
};

export const TituloLongo: Story = {
	args: {
		titulo: "Unidade consumidora 0042 · Rua das Acácias, 1200 · Bairro Centro",
		className: "w-96 bg-surface-1",
	},
};

export const SemTitulo: Story = { args: { titulo: undefined } };

// A página preenche a trilha com `HeaderTrilha`; o título passa a ser o primeiro nível.
export const ComTrilha: Story = {
	render: function Render(args) {
		const [slot, setSlot] = useState<HTMLDivElement | null>(null);
		return (
			<HeaderTrilhaContext value={slot}>
				<Header {...args} trilhaRef={setSlot} />
				<HeaderTrilha>
					<Breadcrumb aria-label="Recorte">
						<BreadcrumbList className="gap-0.5">
							<BreadcrumbSeparator className="mx-0.5" />
							<BreadcrumbItem>
								<Button variant="ghost" size="sm" className="h-7 px-1.5">
									Recife
									<CaretDownIcon
										aria-hidden
										className="size-3 text-text-muted"
									/>
								</Button>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</HeaderTrilha>
			</HeaderTrilhaContext>
		);
	},
};
