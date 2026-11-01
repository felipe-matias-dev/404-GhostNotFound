import { DEFINICOES, type DefinicaoIndicador } from "#/features/indicadores";
import { formatHoras, formatNumero } from "#/lib/format";

/** Os indicadores de continuidade que a comparação devolve, com o nome do campo da API. */
export type IndicadorRede =
	| "dec"
	| "fec"
	| "horas_interrompidas"
	| "n_interrupcoes"
	| "n_uc_medio";

/** Como cada indicador aparece na faixa da Rede e na ajuda da tabela. */
export const INDICADORES_REDE: Record<IndicadorRede, DefinicaoIndicador> = {
	dec: DEFINICOES.dec,
	fec: DEFINICOES.fec,
	horas_interrompidas: {
		label: "Horas interrompidas",
		format: formatHoras,
		favorable: "down",
		hint: "Soma das horas sem energia de cada unidade consumidora atingida (UC·h). Com o mesmo DEC, quem atende mais UCs soma mais horas.",
	},
	n_interrupcoes: {
		label: "Interrupções",
		format: formatNumero,
		favorable: "down",
		hint: "Ocorrências de falta de luz no período, contadas uma vez por unidade consumidora atingida.",
	},
	n_uc_medio: {
		label: "UCs atendidas (média)",
		format: formatNumero,
		favorable: "none",
		hint: "Média mensal das unidades consumidoras faturadas: o divisor do DEC e do FEC.",
	},
};
