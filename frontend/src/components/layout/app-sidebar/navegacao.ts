import {
	BuildingsIcon,
	CurrencyCircleDollarIcon,
	GaugeIcon,
	HouseIcon,
	type Icon,
	LightningSlashIcon,
} from "@phosphor-icons/react";
import {
	type LinkProps,
	useMatches,
	useMatchRoute,
} from "@tanstack/react-router";
import type { ComponentType } from "react";
import { LogoMark } from "#/components/layout/logo";

export type ItemNavegacao = {
	to: NonNullable<LinkProps["to"]>;
	rotulo: string;
	icone:
		| Icon
		| ComponentType<{
				"aria-hidden"?: boolean;
				weight?: "regular" | "fill";
				className?: string;
		  }>;
	grupo: "Minha área" | "Outras consultas";
};

// Ícones de Fundamentos/Ícones ("para a mesma ideia, o mesmo ícone em todas as telas").
export const NAVEGACAO: ItemNavegacao[] = [
	{ to: "/", rotulo: "Visão geral", icone: HouseIcon, grupo: "Minha área" },
	{
		to: "/receita",
		rotulo: "Receita",
		icone: CurrencyCircleDollarIcon,
		grupo: "Minha área",
	},
	{ to: "/rede", rotulo: "Rede", icone: GaugeIcon, grupo: "Minha área" },
	{
		to: "/uc",
		rotulo: "Consulta de UC",
		icone: BuildingsIcon,
		grupo: "Minha área",
	},
	{
		to: "/perdas",
		rotulo: "Perdas",
		icone: LightningSlashIcon,
		grupo: "Minha área",
	},
	{
		to: "/agente",
		rotulo: "Agente",
		icone: LogoMark,
		grupo: "Minha área",
	},
];

export function organizarNavegacao(
	itens: ItemNavegacao[],
	prioritarias: readonly string[],
): ItemNavegacao[] {
	const minhaArea: ItemNavegacao[] = [];
	const outrasConsultas: ItemNavegacao[] = [];
	for (const item of itens) {
		if (prioritarias.includes(item.to)) {
			minhaArea.push({ ...item, grupo: "Minha área" });
		} else {
			outrasConsultas.push({ ...item, grupo: "Outras consultas" });
		}
	}
	return minhaArea.concat(outrasConsultas);
}

// Item ativo do Header e da sidebar. Rotas filhas mantêm a seção (fuzzy), mas um caminho sem
// rota (o "não encontrado") não marca nenhuma.
export function useItemAtivo(itens: ItemNavegacao[]) {
	const matchRoute = useMatchRoute();
	const naoEncontrado = useMatches({
		select: (matches) =>
			matches.some((match) => match._notFound || match.status === "notFound"),
	});
	if (naoEncontrado) return undefined;
	return itens.find(({ to }) => matchRoute({ to, fuzzy: to !== "/" }));
}
