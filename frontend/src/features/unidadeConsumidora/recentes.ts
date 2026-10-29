export const RECENTES_UC_KEY = "venergy:ucs-recentes";

export function adicionarRecente(recentes: string[], codigo: string): string[] {
	return [codigo, ...recentes.filter((item) => item !== codigo)].slice(0, 5);
}

export function parseRecentes(raw: string | null): string[] {
	if (!raw) return [];
	try {
		const data: unknown = JSON.parse(raw);
		if (
			!Array.isArray(data) ||
			!data.every((item) => typeof item === "string" && item.trim().length > 0)
		)
			return [];
		return [...new Set(data.map((item: string) => item.trim()))].slice(0, 5);
	} catch {
		return [];
	}
}
