import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { SegmentedControl } from "#/components/ui/segmented-control";
import { formatBRL, formatHoras, formatNumero, formatPct } from "#/lib/format";
import {
	type TrendCategory,
	TrendChart,
	type TrendSeries,
} from "./trend-chart";

const MESES = [
	"jan",
	"fev",
	"mar",
	"abr",
	"mai",
	"jun",
	"jul",
	"ago",
	"set",
	"out",
	"nov",
	"dez",
];
const ANOS = [2023, 2024, 2025];

// Série sintética: tendência leve de alta e sazonalidade de verão.
const receita = (ano: number, mes: number) =>
	42_000_000 +
	(ano - 2023) * 1_600_000 +
	Math.cos(((mes - 1) / 12) * Math.PI * 2) * 2_400_000 +
	((mes * 7 + ano) % 5) * 180_000;
const dec = (ano: number, mes: number) =>
	1.1 + Math.sin(((mes + 2) / 12) * Math.PI * 2) * 0.35 - (ano - 2023) * 0.08;

const CONTINUA: TrendCategory[] = ANOS.flatMap((ano) =>
	MESES.map((mes, i) => ({
		key: `${ano}-${String(i + 1).padStart(2, "0")}`,
		label: `${mes} ${String(ano).slice(2)}`,
		title: `${mes}/${ano}`,
	})),
);
const MES_DO_ANO: TrendCategory[] = MESES.map((mes, i) => ({
	key: String(i + 1).padStart(2, "0"),
	label: mes,
}));

const continua = (
	id: string,
	label: string,
	valor: (ano: number, mes: number) => number,
): TrendSeries[] => [
	{
		id,
		label,
		values: ANOS.flatMap((ano) => MESES.map((_, i) => valor(ano, i + 1))),
	},
];
const porAno = (valor: (ano: number, mes: number) => number): TrendSeries[] =>
	ANOS.map((ano, i) => ({
		id: String(ano),
		label: String(ano),
		values: MESES.map((_, m) => valor(ano, m + 1)),
		color: i === ANOS.length - 1 ? 1 : i === ANOS.length - 2 ? 2 : "muted",
		emphasis: i === ANOS.length - 1,
	}));

const compacto = (valor: number) => formatBRL(valor, { compacto: true });

const meta = {
	title: "Componentes/TrendChart",
	component: TrendChart,
	tags: ["autodocs"],
	parameters: { layout: "padded" },
	args: {
		label: "Receita faturada por mês",
		categories: CONTINUA,
		series: continua("receita", "Receita faturada", receita),
		formatValue: compacto,
		categoryLabel: "Competência",
	},
	decorators: [
		(Story) => (
			<div className="mx-auto w-full max-w-4xl">
				<Story />
			</div>
		),
	],
} satisfies Meta<typeof TrendChart>;

export default meta;
type Story = StoryObj<typeof meta>;

// Uma série: ela é o destaque (ponto final; área só com `zeroBaseline`). Passe o mouse ou use
// as setas.
export const Padrao: Story = {};

// Duas séries em índice que se afastam: linha de referência em 100, rótulo no fim de cada linha
// no lugar da legenda e a faixa entre as duas, que é o dado do gráfico.
export const Tesoura: Story = {
	args: {
		label: "Receita e energia em índice",
		categories: CONTINUA,
		series: [
			{
				id: "receita",
				label: "Receita faturada",
				shortLabel: "receita",
				values: CONTINUA.map((_, i) => 100 + i * 0.25),
				color: 1,
				emphasis: true,
			},
			{
				id: "energia",
				label: "Energia faturada",
				shortLabel: "energia",
				values: CONTINUA.map((_, i) => 100 - i * 0.11),
				color: 2,
				emphasis: true,
			},
		],
		formatValue: formatNumero,
		reference: 100,
		endLabels: true,
		band: ["receita", "energia"],
	},
};

// Um ano por linha sobre jan–dez: o ano atual em destaque, o anterior em comparação e os
// mais antigos como contexto.
export const AnoAAno: Story = {
	args: {
		label: "Receita faturada, ano a ano",
		categories: MES_DO_ANO,
		series: porAno(receita),
		categoryLabel: "Mês",
	},
};

// Os meses comparados na tela ganham uma régua tracejada e aparecem no tooltip.
export const ComMarcadores: Story = {
	args: {
		markers: [
			{ at: "2024-09", label: "Base" },
			{ at: "2025-09", label: "Atual" },
		],
	},
};

// Rodapé do tooltip: a variação sobre o mês anterior, calculada por quem usa o gráfico.
export const ComRodape: Story = {
	args: {
		tooltipFooter: (i) => {
			const valores = continua("receita", "", receita)[0]?.values ?? [];
			const atual = valores[i];
			const anterior = valores[i - 1];
			if (atual == null || anterior == null)
				return <span className="text-text-muted">Sem mês anterior</span>;
			return (
				<span className="text-text-muted">
					{formatPct((atual - anterior) / anterior, { sinal: true })} vs. mês
					anterior
				</span>
			);
		},
	},
};

// Mês sem dado interrompe a linha; o tooltip e a tabela mostram "—".
export const ComLacunas: Story = {
	args: {
		label: "DEC por mês",
		series: [
			{
				id: "dec",
				label: "DEC",
				values: ANOS.flatMap((ano) =>
					MESES.map((_, i) =>
						ano === 2024 && i >= 3 && i <= 5 ? null : dec(ano, i + 1),
					),
				),
			},
		],
		formatValue: formatHoras,
	},
};

// Troca de indicador (mesmas séries: as linhas mudam de forma) e de visão (séries novas:
// as antigas somem e as novas se desenham).
export const TrocaDeDados: Story = {
	render: (args) => {
		const [indicador, setIndicador] = useState<"receita" | "dec">("receita");
		const [visao, setVisao] = useState<"mes" | "ano">("mes");
		const valor = indicador === "receita" ? receita : dec;
		return (
			<TrendChart
				{...args}
				label={indicador === "receita" ? "Receita faturada" : "DEC"}
				categories={visao === "mes" ? CONTINUA : MES_DO_ANO}
				series={
					visao === "mes"
						? continua(
								"serie",
								indicador === "receita" ? "Receita faturada" : "DEC",
								valor,
							)
						: porAno(valor)
				}
				formatValue={indicador === "receita" ? compacto : formatHoras}
				toolbar={
					<>
						<SegmentedControl
							label="Indicador"
							value={indicador}
							onValueChange={setIndicador}
							options={[
								{ value: "receita", label: "Receita" },
								{ value: "dec", label: "DEC" },
							]}
						/>
						<SegmentedControl
							label="Visão"
							value={visao}
							onValueChange={setVisao}
							options={[
								{ value: "mes", label: "Mês a mês" },
								{ value: "ano", label: "Ano a ano" },
							]}
						/>
					</>
				}
			/>
		);
	},
};

// Coluna estreita (celular): o eixo x mostra só os rótulos que cabem.
export const Estreito: Story = {
	decorators: [
		(Story) => (
			<div className="w-80">
				<Story />
			</div>
		),
	],
};

// `height="fill"`: o gráfico ocupa a altura que sobra no pai (aqui, 480px).
export const PreencheAltura: Story = {
	args: { height: "fill", className: "flex-1" },
	decorators: [
		(Story) => (
			<div className="flex h-120 flex-col">
				<Story />
			</div>
		),
	],
};

export const Carregando: Story = {
	args: { categories: undefined, series: undefined, loading: true },
};

export const Erro: Story = {
	args: {
		series: undefined,
		error: "Não foi possível carregar a série.",
		onRetry: () => {},
	},
};

export const Vazio: Story = {
	args: { categories: [], series: [], emptyMessage: "Sem meses carregados." },
};
