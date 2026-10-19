export const API_URL = (import.meta.env.VITE_API_URL || "/api").replace(
	/\/+$/,
	"",
);

export class ApiError extends Error {
	readonly status: number;
	/** Corpo da resposta de erro (JSON do FastAPI, ex.: `{ detail }`, ou texto). */
	readonly body: unknown;

	constructor(status: number, body: unknown) {
		super(`API respondeu ${status}`);
		this.name = "ApiError";
		this.status = status;
		this.body = body;
	}
}

async function readBody(response: Response): Promise<unknown> {
	const text = await response.text();
	if (!text) return null;
	try {
		return JSON.parse(text);
	} catch {
		return text;
	}
}

/** `path` relativo à base da API, começando com "/" (ex.: "/ucs/123"). */
export async function apiFetch<T>(
	path: string,
	init?: RequestInit,
): Promise<T> {
	const headers = new Headers(init?.headers);
	if (!headers.has("Accept")) headers.set("Accept", "application/json");

	const response = await fetch(`${API_URL}${path}`, { ...init, headers });
	const body = await readBody(response);

	if (!response.ok) throw new ApiError(response.status, body);
	return body as T;
}
