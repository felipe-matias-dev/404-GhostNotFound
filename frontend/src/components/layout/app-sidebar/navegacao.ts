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

export type ItemNavegacao = {
	to: NonNullable<LinkProps["to"]>;
	rotulo: string;
	icone: Icon;
	grupo: "Análise" | "Operação";
};

// Ícones de Fundamentos/Ícones ("para a mesma ideia, o mesmo ícone em todas as telas").
export const NAVEGACAO: ItemNavegacao[] = [
	{ to: "/", rotulo: "Visão geral", icone: HouseIcon, grupo: "Análise" },
	{
		to: "/receita",
		rotulo: "Receita",
		icone: CurrencyCircleDollarIcon,
		grupo: "Análise",
	},
	{ to: "/rede", rotulo: "Rede", icone: GaugeIcon, grupo: "Análise" },
	{
		to: "/uc",
		rotulo: "Consulta de UC",
		icone: BuildingsIcon,
		grupo: "Operação",
	},
	{
		to: "/perdas",
		rotulo: "Perdas",
		icone: LightningSlashIcon,
		grupo: "Operação",
	},
];

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
