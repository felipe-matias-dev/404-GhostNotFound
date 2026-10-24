import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { formatBRL, formatKWh } from "#/lib/format";
import { DataTable, type DataTableColumn } from "./data-table";

type Uc = {
	cod_uc: string;
	municipio: string;
	classe: string;
	consumo: number;
	receita: number | null;
};

const MUNICIPIOS = ["Recife", "Olinda", "Paulista", "Jaboatão", "Cabo"];
const CLASSES = ["B1", "B2", "B3", "A4"];

const UCS: Uc[] = Array.from({ length: 23 }, (_, i) => ({
	cod_uc: String(i + 1).padStart(4, "0"),
	municipio: MUNICIPIOS[(i * 3) % MUNICIPIOS.length] ?? "Recife",
	classe: CLASSES[(i * 7) % CLASSES.length] ?? "B1",
	consumo: 80 + ((i * 137) % 900),
	receita: i % 9 === 4 ? null : 60 + ((i * 211) % 1400) + (i % 3) * 0.45,
}));

const COLUNAS: DataTableColumn<Uc>[] = [
	{ id: "cod_uc", header: "UC", width: "88px", value: (u) => u.cod_uc },
	{ id: "municipio", header: "Município", value: (u) => u.municipio },
	{
		id: "classe",
		header: "Classe",
		width: "96px",
		value: (u) => u.classe,
		cell: (u) => <Badge>{u.classe}</Badge>,
	},
	{
		id: "consumo",
		header: "Consumo",
		width: "120px",
		align: "end",
		numeric: true,
		value: (u) => u.consumo,
		cell: (u) => formatKWh(u.consumo),
	},
	{
		id: "receita",
		header: "Receita",
		width: "128px",
		align: "end",
		numeric: true,
		value: (u) => u.receita,
		cell: (u) => formatBRL(u.receita),
	},
];

const meta = {
	title: "Componentes/DataTable",
	component: DataTable<Uc>,
	tags: ["autodocs"],
	parameters: { layout: "padded" },
	args: {
		label: "Unidades consumidoras",
		columns: COLUNAS,
		rows: UCS,
		getRowId: (u: Uc) => u.cod_uc,
		getRowLabel: (u: Uc) => `UC ${u.cod_uc}`,
		pageSize: 8,
	},
	decorators: [
		(Story) => (
			<div className="mx-auto w-full max-w-4xl">
				<Story />
			</div>
		),
	],
} satisfies Meta<typeof DataTable<Uc>>;

export default meta;
type Story = StoryObj<typeof meta>;

// Clique no cabeçalho: crescente, decrescente e de volta à ordem original. As linhas viajam.
export const Padrao: Story = {};

export const OrdenadoPorReceita: Story = {
	args: { defaultSort: { columnId: "receita", direction: "desc" } },
};

export const Carregando: Story = { args: { rows: undefined, loading: true } };

export const Erro: Story = {
	args: {
		rows: undefined,
		error: "Não foi possível carregar as unidades consumidoras.",
		onRetry: () => {},
	},
};

export const Vazio: Story = {
	args: { rows: [], emptyMessage: "Nenhuma UC neste recorte." },
};

// Seleção controlada; o cabeçalho marca ou desmarca a página inteira.
export const SelecaoMultipla: Story = {
	render: function Render(args) {
		const [selected, setSelected] = useState<Set<string>>(
			() => new Set(["0002", "0005"]),
		);
		return (
			<DataTable {...args} selected={selected} onSelectedChange={setSelected} />
		);
	},
};

// Linha clicável (drill-down): a primeira coluna vira botão e a linha inteira responde.
export const LinhaClicavel: Story = {
	render: function Render(args) {
		const [aberta, setAberta] = useState<string | null>(null);
		return (
			<div className="flex flex-col gap-3">
				<DataTable {...args} onRowClick={(u) => setAberta(u.cod_uc)} />
				<p className="text-small text-text-muted">
					Última aberta: {aberta ? `UC ${aberta}` : "nenhuma"}
				</p>
			</div>
		);
	},
};

function AcoesDaUc() {
	return (
		<>
			<Button size="xs" variant="outline">
				Inspecionar
			</Button>
			<Button size="xs" variant="ghost">
				Ignorar
			</Button>
		</>
	);
}

// Ações por linha: última coluna na tabela e rodapé nos cards; o clique no botão não abre a linha.
export const ComAcoes: Story = {
	args: { rowActionsWidth: "200px", pageSize: 5 },
	render: function Render(args) {
		const [aberta, setAberta] = useState<string | null>(null);
		return (
			<div className="flex flex-col gap-6">
				<DataTable
					{...args}
					onRowClick={(u) => setAberta(u.cod_uc)}
					rowActions={() => <AcoesDaUc />}
				/>
				<p className="text-small text-text-muted">
					Última aberta: {aberta ? `UC ${aberta}` : "nenhuma"}
				</p>
				<div className="mx-auto w-[360px]">
					<DataTable
						{...args}
						label="Unidades consumidoras em container estreito"
						pageSize={3}
						onRowClick={(u) => setAberta(u.cod_uc)}
						rowActions={() => <AcoesDaUc />}
					/>
				</div>
			</div>
		);
	},
};

// Abaixo de 48rem de container a tabela vira lista de cards, com a ordenação em chips.
export const Celular: Story = {
	parameters: { viewport: { defaultViewport: "mobile1" } },
	decorators: [
		(Story) => (
			<div className="mx-auto w-[360px]">
				<Story />
			</div>
		),
	],
	render: function Render(args) {
		const [selected, setSelected] = useState<Set<string>>(() => new Set());
		return (
			<DataTable
				{...args}
				pageSize={5}
				selected={selected}
				onSelectedChange={setSelected}
			/>
		);
	},
};
