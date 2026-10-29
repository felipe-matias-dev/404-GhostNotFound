import createClient from "openapi-fetch";
import type { paths } from "./api-schema.gen";

export const API_URL = (import.meta.env.VITE_API_URL || "/api").replace(
	/\/+$/,
	"",
);

/**
 * Client tipado pelo contrato `contracts/openapi.json` (tipos em `api-schema.gen.ts`,
 * gerados por `npm run gen:api`). Rota, parâmetros e resposta erram na compilação.
 */
export const api = createClient<paths>({
	baseUrl: API_URL,
	credentials: "include",
	headers: { Accept: "application/json" },
});

api.use({
	onResponse({ request, response }) {
		if (
			response.status === 401 &&
			!new URL(request.url).pathname.match(/\/auth\/(login|me|logout)$/) &&
			typeof window !== "undefined"
		) {
			window.dispatchEvent(new Event("venergy:session-expired"));
		}
	},
});

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

/**
 * Devolve o `data` de uma chamada do `api` ou lança `ApiError`, para que o TanStack Query
 * receba a falha em `error`. Ex.: `unwrap(api.GET("/rota/{id}", { params: { path: { id } } }))`.
 */
export async function unwrap<T>(
	request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
	const { data, error, response } = await request;
	if (!response.ok) throw new ApiError(response.status, error);
	return data as T;
}
