import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { formatBRL } from "#/lib/format";
import { RegionMap } from "./region-map";
import { RMR_CONTEXTO, RMR_MUNICIPIOS, RMR_VIEWBOX } from "./rmr.gen";
import { RMR_BAIRROS } from "./rmr-bairros.gen";

const RECIFE = RMR_MUNICIPIOS.find((m) => m.nome === "Recife");

const COM_DADO = new Set(
	RMR_MUNICIPIOS.filter((m) =>
		[
			"Recife",
			"Olinda",
			"Paulista",
			"Jaboatão dos Guararapes",
			"Cabo de Santo Agostinho",
		].includes(m.nome),
	).map((m) => m.id),
);

const meta = {
	title: "Componentes/RegionMap",
	component: RegionMap,
	tags: ["autodocs"],
	args: {
		label: "Mapa da Região Metropolitana do Recife",
		viewBox: RMR_VIEWBOX,
		shapes: RMR_MUNICIPIOS,
		context: RMR_CONTEXTO,
		getHref: (m) => `#${m.id}`,
		onSelect: () => {},
		className: "h-[36rem] w-72",
	},
	render: function Render(args) {
		const [selecionado, setSelecionado] = useState(args.selectedId ?? null);
		return (
			<RegionMap
				{...args}
				selectedId={selecionado}
				onSelect={(m) => setSelecionado(m.id)}
				onClear={() => setSelecionado(null)}
				clearLabel="Todos os municípios"
			/>
		);
	},
} satisfies Meta<typeof RegionMap>;

export default meta;
type Story = StoryObj<typeof meta>;

// Clique num município: o mapa enquadra; arraste, Ctrl+roda e os botões dão zoom.
export const Padrao: Story = {};

// Só os municípios com dado são links; os outros da RMR ficam apagados.
export const ComDadoParcial: Story = {
	args: {
		enabledIds: COM_DADO,
		describe: (m) =>
			COM_DADO.has(m.id) ? `Variação: ${formatBRL(1473.12)}` : null,
	},
};

export const Selecionado: Story = {
	args: {
		selectedId: RMR_MUNICIPIOS.find((m) => m.nome === "Recife")?.id ?? null,
	},
};

// Antes do dado chegar: nenhum município clicável.
export const Carregando: Story = { args: { enabledIds: new Set() } };

// Município escolhido com os bairros dele por cima: o contorno do município fica em accent.
export const ComBairros: Story = {
	args: {
		shapes: [
			...RMR_MUNICIPIOS,
			...(RECIFE ? (RMR_BAIRROS[RECIFE.id] ?? []) : []),
		],
		selectedId: RECIFE?.id ?? null,
		containerIds: RECIFE ? new Set([RECIFE.id]) : undefined,
	},
};

// Intensidade fictícia e estável por região, de -1 a 1, só para ver a escala e o brilho.
const intensidade = (id: string) => ((Number(id.slice(-3)) * 37) % 21) / 10 - 1;

// Escala contínua com brilho nas mais fortes: bairros de Recife e municípios com dado.
export const ColoridoPorVariacao: Story = {
	args: {
		...ComBairros.args,
		getIntensity: (m) => intensidade(m.id),
		legend: {
			title: "Variação da receita",
			ticks: ["−10%", "0", "+10%"],
			description: "vermelho para queda, verde para alta",
		},
	},
};

// Sem recorte: todos os municípios coloridos.
export const MunicipiosColoridos: Story = {
	args: {
		getIntensity: (m) => intensidade(m.id),
		legend: ColoridoPorVariacao.args?.legend,
	},
};

const BOA_VIAGEM = RECIFE
	? RMR_BAIRROS[RECIFE.id]?.find((b) => b.nome === "Boa Viagem")
	: undefined;

// Bairro escolhido: só ele fica na cor; o resto do mapa apaga e vira contexto.
export const BairroEmFoco: Story = {
	args: {
		...ColoridoPorVariacao.args,
		selectedId: BOA_VIAGEM?.id ?? null,
		focusIds: BOA_VIAGEM ? new Set([BOA_VIAGEM.id]) : undefined,
	},
};
