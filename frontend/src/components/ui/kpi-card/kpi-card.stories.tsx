import type { Meta, StoryObj } from "@storybook/react-vite";
import { Link } from "@tanstack/react-router";
import { formatBRL, formatKWh, formatNumero } from "#/lib/format";
import { KpiCard } from "./kpi-card";

const receita = (valor: number) => formatBRL(valor, { compacto: true });
const energia = (valor: number) => formatKWh(valor, { compacto: true });
const horas = (valor: number) => `${formatNumero(valor)} h`;

const meta = {
	title: "Componentes/KpiCard",
	component: KpiCard,
	tags: ["autodocs"],
	args: {
		label: "Receita faturada",
		value: 45_712_401.17,
		format: receita,
		delta: { value: -0.052, comparison: "vs. set/2025" },
	},
	argTypes: {
		format: { control: false },
		link: { control: false },
		hint: { control: "text" },
	},
	decorators: [
		(Story) => (
			<div className="w-72">
				<Story />
			</div>
		),
	],
} satisfies Meta<typeof KpiCard>;

export default meta;
type Story = StoryObj<typeof meta>;

// Queda de receita: seta para baixo, sinal e `danger` (a direção boa é "up", o padrão).
export const Padrao: Story = {};

// O KPI que importa na tela: número em `accent-text`. Um por região, no máximo.
export const Destaque: Story = {
	args: {
		highlight: true,
		delta: { value: 0.039, comparison: "vs. set/2025" },
	},
};

// Menor é melhor: o DEC caiu, então a seta desce em `success`. O (i) abre a definição.
export const MenorEMelhor: Story = {
	args: {
		label: "DEC",
		value: 12.43,
		format: horas,
		hint: "Duração equivalente de interrupção: horas sem energia, em média, por unidade consumidora no mês.",
		delta: { value: -0.081, favorable: "down", comparison: "vs. set/2025" },
	},
};

// Sem juízo: consumo maior não é bom nem ruim. A seta fica, a cor sai.
export const Neutro: Story = {
	args: {
		label: "Energia faturada",
		value: 18_342_910,
		format: energia,
		delta: { value: 0.024, favorable: "none", comparison: "vs. set/2025" },
	},
};

// Variação que arredonda para zero: sem seta, em `text-muted`.
export const Estavel: Story = {
	args: { delta: { value: 0.0002, comparison: "vs. set/2025" } },
};

// Variação em valor absoluto, com o formatador do próprio valor.
export const VariacaoAbsoluta: Story = {
	args: {
		delta: {
			value: -2_502_928.95,
			format: (valor) => formatBRL(valor, { sinal: true, compacto: true }),
			comparison: "vs. set/2025",
		},
	},
};

export const SemVariacao: Story = { args: { delta: undefined } };

// O card inteiro leva à tela de detalhe; o (i) continua abrindo a definição por cima.
export const ComLink: Story = {
	parameters: { rota: "/" },
	args: {
		link: <Link to="/receita" />,
		hint: "Soma das faturas emitidas na competência, com tributos.",
	},
};

// Conteúdo extra abaixo do número (nota, minigráfico).
export const ComConteudo: Story = {
	args: {
		label: "Chamados",
		value: 3_412,
		format: formatNumero,
		delta: { value: 0.12, favorable: "down", comparison: "vs. set/2025" },
		children: (
			<p className="border-t border-border pt-3 text-small text-text-muted">
				62% sobre falta de energia.
			</p>
		),
	},
};

// Abaixo de 16rem de largura o valor desce para `text-title`.
export const Estreito: Story = {
	decorators: [
		(Story) => (
			<div className="w-52">
				<Story />
			</div>
		),
	],
};

// Composição típica (Visão geral): grade que se ajusta à largura, cards da mesma altura.
export const Grade: Story = {
	parameters: { layout: "padded", rota: "/" },
	decorators: [
		(Story) => (
			<div className="w-screen max-w-6xl">
				<Story />
			</div>
		),
	],
	render: () => (
		<div className="grid grid-cols-[repeat(auto-fit,minmax(15rem,1fr))] gap-3">
			<KpiCard
				label="Receita faturada"
				value={45_712_401.17}
				format={receita}
				highlight
				link={<Link to="/receita" />}
				delta={{ value: -0.052, comparison: "vs. set/2025" }}
			/>
			<KpiCard
				label="Energia faturada"
				value={18_342_910}
				format={energia}
				delta={{ value: 0.024, favorable: "none", comparison: "vs. set/2025" }}
			/>
			<KpiCard
				label="DEC"
				value={12.43}
				format={horas}
				hint="Duração equivalente de interrupção: horas sem energia, em média, por unidade consumidora no mês."
				link={<Link to="/rede" />}
				delta={{ value: -0.081, favorable: "down", comparison: "vs. set/2025" }}
			/>
			<KpiCard
				label="Satisfação média"
				value={null}
				emptyMessage="Pesquisa ainda não fechada."
			/>
		</div>
	),
};

export const Carregando: Story = { args: { value: undefined, loading: true } };

export const Erro: Story = {
	args: {
		value: undefined,
		error: "Não foi possível carregar.",
		onRetry: () => {},
	},
};

export const Vazio: Story = {
	args: {
		value: null,
		delta: undefined,
		emptyMessage: "Sem faturas nesta competência.",
	},
};
