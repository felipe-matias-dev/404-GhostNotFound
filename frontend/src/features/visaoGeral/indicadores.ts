import {
	formatBRL,
	formatHoras,
	formatIndice,
	formatKWh,
	formatNumero,
} from "#/lib/format";
import type { Indicador } from "./types";

export type DefinicaoIndicador = {
	label: string;
	format: (valor: number) => string;
	/** Direção que é melhora: define o verde e o vermelho da variação. */
	favorable: "up" | "down";
	hint: string;
};

/** Como cada indicador da diretoria aparece: nos cards e no gráfico de tendência. */
export const DEFINICOES: Record<Indicador, DefinicaoIndicador> = {
	receita_faturada: {
		label: "Receita faturada",
		format: (valor) => formatBRL(valor, { compacto: true }),
		favorable: "up",
		hint: "Soma das faturas emitidas no período, com tributos.",
	},
	kwh_faturado: {
		label: "Energia faturada",
		format: (valor) => formatKWh(valor, { compacto: true }),
		favorable: "up",
		hint: "kWh faturados no período, somados de todas as unidades consumidoras.",
	},
	dec: {
		label: "DEC",
		format: formatHoras,
		favorable: "down",
		hint: "Duração equivalente de interrupção: horas sem energia, em média, por unidade consumidora no período.",
	},
	fec: {
		label: "FEC",
		format: formatIndice,
		favorable: "down",
		hint: "Frequência equivalente de interrupção: quantas vezes, em média, cada unidade consumidora ficou sem energia no período.",
	},
	n_chamados: {
		label: "Chamados",
		format: formatNumero,
		favorable: "down",
		hint: "Chamados de atendimento abertos no período.",
	},
	satisfacao_media: {
		label: "Satisfação média",
		format: formatNumero,
		favorable: "up",
		hint: "Média das notas de 1 a 5 dos chamados avaliados no período; chamado sem nota fica fora.",
	},
};
