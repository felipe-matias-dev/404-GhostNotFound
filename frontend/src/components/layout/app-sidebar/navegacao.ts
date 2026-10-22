import {
	BuildingsIcon,
	CurrencyCircleDollarIcon,
	GaugeIcon,
	HouseIcon,
	type Icon,
	LightningSlashIcon,
} from "@phosphor-icons/react";
import type { LinkProps } from "@tanstack/react-router";

export type ItemNavegacao = {
	to: NonNullable<LinkProps["to"]>;
	rotulo: string;
	icone: Icon;
};

// Ícones de Fundamentos/Ícones ("para a mesma ideia, o mesmo ícone em todas as telas").
export const NAVEGACAO: ItemNavegacao[] = [
	{ to: "/", rotulo: "Visão geral", icone: HouseIcon },
	{ to: "/receita", rotulo: "Receita", icone: CurrencyCircleDollarIcon },
	{ to: "/uc", rotulo: "Unidade consumidora", icone: BuildingsIcon },
	{ to: "/perdas", rotulo: "Perdas", icone: LightningSlashIcon },
	{ to: "/rede", rotulo: "Rede", icone: GaugeIcon },
];
