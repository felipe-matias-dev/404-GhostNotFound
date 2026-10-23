import type { Meta, StoryObj } from "@storybook/react-vite";
import {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbLink,
	BreadcrumbList,
	BreadcrumbPage,
	BreadcrumbSeparator,
} from "./breadcrumb";

const meta = {
	title: "Componentes/Breadcrumb",
	component: Breadcrumb,
	tags: ["autodocs"],
} satisfies Meta<typeof Breadcrumb>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {
	render: () => (
		<Breadcrumb aria-label="Recorte">
			<BreadcrumbList>
				<BreadcrumbItem>
					<BreadcrumbLink href="#receita">Receita</BreadcrumbLink>
				</BreadcrumbItem>
				<BreadcrumbSeparator />
				<BreadcrumbItem>
					<BreadcrumbLink href="#recife">Recife</BreadcrumbLink>
				</BreadcrumbItem>
				<BreadcrumbSeparator />
				<BreadcrumbItem>
					<BreadcrumbPage>Boa Viagem</BreadcrumbPage>
				</BreadcrumbItem>
			</BreadcrumbList>
		</Breadcrumb>
	),
};

// Nome longo num espaço estreito (header no celular): o nível trunca.
export const Estreito: Story = {
	render: () => (
		<div className="w-56">
			<Breadcrumb aria-label="Recorte">
				<BreadcrumbList>
					<BreadcrumbItem>
						<BreadcrumbLink href="#receita">Receita</BreadcrumbLink>
					</BreadcrumbItem>
					<BreadcrumbSeparator />
					<BreadcrumbItem>
						<BreadcrumbPage>Jaboatão dos Guararapes</BreadcrumbPage>
					</BreadcrumbItem>
				</BreadcrumbList>
			</Breadcrumb>
		</div>
	),
};
