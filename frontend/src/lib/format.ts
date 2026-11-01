const VAZIO = "—";

const brl = new Intl.NumberFormat("pt-BR", {
	style: "currency",
	currency: "BRL",
});
// "exceptZero": "+" na alta, "-" na queda e nada no zero, decidido sobre o valor já arredondado.
const brlComSinal = new Intl.NumberFormat("pt-BR", {
	style: "currency",
	currency: "BRL",
	signDisplay: "exceptZero",
});
// Compacto para números de destaque: 45712401.17 → "R$ 45,7 mi".
const brlCompacto = new Intl.NumberFormat("pt-BR", {
	style: "currency",
	currency: "BRL",
	notation: "compact",
	minimumFractionDigits: 0,
	maximumFractionDigits: 1,
});
const brlCompactoComSinal = new Intl.NumberFormat("pt-BR", {
	style: "currency",
	currency: "BRL",
	notation: "compact",
	minimumFractionDigits: 0,
	maximumFractionDigits: 1,
	signDisplay: "exceptZero",
});
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const inteiroComSinal = new Intl.NumberFormat("pt-BR", {
	maximumFractionDigits: 0,
	signDisplay: "exceptZero",
});
const numeroCompacto = new Intl.NumberFormat("pt-BR", {
	notation: "compact",
	maximumFractionDigits: 1,
});
const numeroCompactoComSinal = new Intl.NumberFormat("pt-BR", {
	notation: "compact",
	maximumFractionDigits: 1,
	signDisplay: "exceptZero",
});
const percentual = new Intl.NumberFormat("pt-BR", {
	style: "percent",
	maximumFractionDigits: 1,
});
const percentualComSinal = new Intl.NumberFormat("pt-BR", {
	style: "percent",
	maximumFractionDigits: 1,
	signDisplay: "exceptZero",
});
const decimal1 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const decimal2 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
// Datas sem hora ("2025-03-10") são interpretadas em UTC; formatar em UTC evita mostrar o dia anterior.
const data = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });
// Instantes com fuso ("2026-10-23T13:30:26Z") ficam no fuso de quem vê a tela.
const dataHora = new Intl.DateTimeFormat("pt-BR", {
	dateStyle: "short",
	timeStyle: "short",
});

/** Abreviações de mês de `#/lib/format`: rótulos de eixo e de calendário. */
export const MESES = [
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

type Valor = number | null | undefined;

/** 1234.5 → "R$ 1.234,50"; com sinal: "+R$ 1.234,50"; compacto: 45712401 → "R$ 45,7 mi" */
export function formatBRL(
	valor: Valor,
	{ sinal = false, compacto = false } = {},
): string {
	if (valor == null) return VAZIO;
	if (compacto)
		return (sinal ? brlCompactoComSinal : brlCompacto).format(valor);
	return (sinal ? brlComSinal : brl).format(valor);
}

/** 1234.5 → "1.235 kWh"; com sinal: "+1.235 kWh"; compacto: 12345678 → "12,3 mi kWh" */
export function formatKWh(
	valor: Valor,
	{ sinal = false, compacto = false } = {},
): string {
	if (valor == null) return VAZIO;
	const numero = compacto
		? sinal
			? numeroCompactoComSinal
			: numeroCompacto
		: sinal
			? inteiroComSinal
			: inteiro;
	return `${numero.format(valor)} kWh`;
}

/** Número sem unidade, até uma casa: 12.43 → "12,4"; 1234 → "1.234" */
export function formatNumero(valor: Valor): string {
	return valor == null ? VAZIO : decimal1.format(valor);
}

/** Índice por unidade consumidora, até duas casas (FEC): 0.347 → "0,35" */
export function formatIndice(valor: Valor): string {
	return valor == null ? VAZIO : decimal2.format(valor);
}

/** Horas, até duas casas (DEC): 1.254 → "1,25 h" */
export function formatHoras(valor: Valor): string {
	return valor == null ? VAZIO : `${decimal2.format(valor)} h`;
}

/** Fração → percentual: -0.039 → "-3,9%"; com sinal, 0.039 → "+3,9%" */
export function formatPct(fracao: Valor, { sinal = false } = {}): string {
	if (fracao == null) return VAZIO;
	return (sinal ? percentualComSinal : percentual).format(fracao);
}

/** Competência "2025-03" → "mar/2025" */
export function formatCompetencia(
	competencia: string | null | undefined,
): string {
	if (!competencia) return VAZIO;
	const match = /^(\d{4})-(\d{2})$/.exec(competencia);
	const mes = match ? MESES[Number(match[2]) - 1] : undefined;
	return match && mes ? `${mes}/${match[1]}` : competencia;
}

/** Competência "2025-03" → "mar 25": rótulo de eixo, onde cabe pouco */
export function formatCompetenciaCurta(
	competencia: string | null | undefined,
): string {
	if (!competencia) return VAZIO;
	const match = /^\d{2}(\d{2})-(\d{2})$/.exec(competencia);
	const mes = match ? MESES[Number(match[2]) - 1] : undefined;
	return match && mes ? `${mes} ${match[1]}` : competencia;
}

/** Número do mês (1 a 12) → "mar" */
export function formatMes(mes: number): string {
	return MESES[mes - 1] ?? VAZIO;
}

/** Período "2024-01/2024-12" → "jan/2024 a dez/2024" */
export function formatPeriodo(periodo: string | null | undefined): string {
	if (!periodo) return VAZIO;
	const [inicio, fim] = periodo.split("/");
	if (!inicio || !fim) return formatCompetencia(periodo);
	return `${formatCompetencia(inicio)} a ${formatCompetencia(fim)}`;
}

/**
 * Período em forma curta, para seletores: "2025-01/2025-12" → "jan–dez 2025",
 * "2025-03/2025-03" → "mar 2025", "2024-07/2025-06" → "jul 2024–jun 2025".
 */
export function formatPeriodoCurto(periodo: string | null | undefined): string {
	if (!periodo) return VAZIO;
	const match = /^(\d{4})-(\d{2})\/(\d{4})-(\d{2})$/.exec(periodo);
	if (!match) return formatPeriodo(periodo);
	const [, ai, mi, af, mf] = match;
	const inicio = MESES[Number(mi) - 1];
	const fim = MESES[Number(mf) - 1];
	if (ai !== af) return `${inicio} ${ai}–${fim} ${af}`;
	return mi === mf ? `${inicio} ${af}` : `${inicio}–${fim} ${af}`;
}

/** Data ISO "2025-03-10" → "10/03/2025" */
export function formatData(iso: string | null | undefined): string {
	if (!iso) return VAZIO;
	const date = new Date(iso);
	return Number.isNaN(date.getTime()) ? iso : data.format(date);
}

/** Instante ISO "2026-10-23T13:30:26Z" → "23/10/2026, 10:30" (fuso local) */
export function formatDataHora(iso: string | null | undefined): string {
	if (!iso) return VAZIO;
	const date = new Date(iso);
	return Number.isNaN(date.getTime()) ? iso : dataHora.format(date);
}

/** Milissegundos → segundos por extenso: 1800 → "1,8 segundos", 1000 → "1 segundo" */
export function formatSegundos(ms: number): string {
	const segundos = ms / 1000;
	return `${decimal1.format(segundos)} ${segundos === 1 ? "segundo" : "segundos"}`;
}

const SEGUNDOS_POR_MINUTO = 60;
const SEGUNDOS_POR_HORA = 3600;
const SEGUNDOS_POR_DIA = 86_400;

/**
 * Tempo decorrido, com a unidade que cabe no tamanho: segundos só na primeira hora, depois
 * horas e minutos, depois dias e horas. 42 → "42 s", 728 → "12 min 08 s", 12 000 → "3 h 20 min",
 * 191 000 → "2 d 5 h". Negativo ou inválido vira "0 s".
 */
export function formatTempoDecorrido(segundos: number): string {
	const total = Number.isFinite(segundos)
		? Math.max(0, Math.floor(segundos))
		: 0;
	if (total < SEGUNDOS_POR_MINUTO) return `${total} s`;
	if (total < SEGUNDOS_POR_HORA) {
		const minutos = Math.floor(total / SEGUNDOS_POR_MINUTO);
		const resto = String(total % SEGUNDOS_POR_MINUTO).padStart(2, "0");
		return `${minutos} min ${resto} s`;
	}
	if (total < SEGUNDOS_POR_DIA) {
		const horas = Math.floor(total / SEGUNDOS_POR_HORA);
		const minutos = String(
			Math.floor((total % SEGUNDOS_POR_HORA) / SEGUNDOS_POR_MINUTO),
		).padStart(2, "0");
		return `${horas} h ${minutos} min`;
	}
	const dias = Math.floor(total / SEGUNDOS_POR_DIA);
	const horas = Math.floor((total % SEGUNDOS_POR_DIA) / SEGUNDOS_POR_HORA);
	return `${dias} d ${horas} h`;
}
