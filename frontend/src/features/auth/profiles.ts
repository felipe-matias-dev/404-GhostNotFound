import type { Profile } from "./api";

export const PROFILES = {
	diretoria: {
		label: "Diretoria",
		home: "/",
		primaryRoutes: ["/", "/receita", "/rede", "/uc"],
	},
	atendimento: { label: "Atendimento", home: "/uc", primaryRoutes: ["/uc"] },
	perdas: {
		label: "Perdas",
		home: "/perdas",
		primaryRoutes: ["/perdas", "/uc"],
	},
	operacao: {
		label: "Operação",
		home: "/rede",
		primaryRoutes: ["/rede", "/uc"],
	},
	ti: {
		label: "TI",
		home: "/",
		primaryRoutes: ["/", "/receita", "/rede", "/uc", "/perdas"],
	},
} as const satisfies Record<
	Profile,
	{ label: string; home: string; primaryRoutes: readonly string[] }
>;

export function loginDestination(profile: Profile, redirect?: string): string {
	if (redirect) {
		const path = redirect.split(/[?#]/, 1)[0];
		if (
			["/", "/receita", "/rede", "/uc", "/perdas"].includes(path) &&
			!redirect.includes("\\")
		)
			return redirect;
	}
	return PROFILES[profile].home;
}
