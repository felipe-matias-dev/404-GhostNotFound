import { ApiError, api, unwrap } from "#/lib/api";
import type { components } from "#/lib/api-schema.gen";

export type User = components["schemas"]["UsuarioLogado"];
export type Profile = User["perfil"];
export type Credentials = components["schemas"]["LoginSchema"];
export const SESSION_KEY = ["auth", "session"] as const;

export async function getSession(): Promise<User | null> {
	try {
		return await unwrap(api.GET("/auth/me"));
	} catch (error) {
		if (error instanceof ApiError && error.status === 401) return null;
		throw error;
	}
}

export const signIn = (credentials: Credentials) =>
	unwrap(api.POST("/auth/login", { body: credentials }));

export const signOut = () => unwrap(api.POST("/auth/logout"));
