const VAZIO = "—";

const brl = new Intl.NumberFormat("pt-BR", {
	style: "currency",
	currency: "BRL",
});
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const percentual = new Intl.NumberFormat("pt-BR", {
	style: "percent",
	maximumFractionDigits: 1,
});
// Datas sem hora ("2025-03-10") são interpretadas em UTC; formatar em UTC evita mostrar o dia anterior.
const data = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });

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

type Valor = number | null | undefined;

/** 1234.5 → "R$ 1.234,50" */
export function formatBRL(valor: Valor): string {
	return valor == null ? VAZIO : brl.format(valor);
}

/** 1234.5 → "1.235 kWh" */
export function formatKWh(valor: Valor): string {
	return valor == null ? VAZIO : `${inteiro.format(valor)} kWh`;
}

/** Fração → percentual: -0.039 → "-3,9%" */
export function formatPct(fracao: Valor): string {
	return fracao == null ? VAZIO : percentual.format(fracao);
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

/** Data ISO "2025-03-10" → "10/03/2025" */
export function formatData(iso: string | null | undefined): string {
	if (!iso) return VAZIO;
	const date = new Date(iso);
	return Number.isNaN(date.getTime()) ? iso : data.format(date);
}
