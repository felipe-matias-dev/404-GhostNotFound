import type { Profile } from "./api";

export const PROFILES = {
	diretoria: {
		label: "Diretoria",
		home: "/",
		primaryRoutes: ["/", "/receita", "/rede", "/uc", "/agente"],
	},
	atendimento: {
		label: "Atendimento",
		home: "/uc",
		primaryRoutes: ["/uc", "/agente"],
	},
	perdas: {
		label: "Perdas",
		home: "/perdas",
		primaryRoutes: ["/perdas", "/uc", "/agente"],
	},
	operacao: {
		label: "Operação",
		home: "/rede",
		primaryRoutes: ["/rede", "/uc", "/agente"],
	},
	ti: {
		label: "TI",
		home: "/",
		primaryRoutes: ["/", "/receita", "/rede", "/uc", "/perdas", "/agente"],
	},
} as const satisfies Record<
	Profile,
	{ label: string; home: string; primaryRoutes: readonly string[] }
>;

export function loginDestination(profile: Profile, redirect?: string): string {
	if (redirect) {
		const path = redirect.split(/[?#]/, 1)[0];
		if (
			["/", "/receita", "/rede", "/uc", "/perdas", "/agente"].includes(path) &&
			!redirect.includes("\\")
		)
			return redirect;
	}
	return PROFILES[profile].home;
}
