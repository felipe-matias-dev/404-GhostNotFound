import { KanbanIcon, TableIcon } from "@phosphor-icons/react";
import { Button } from "#/components/ui/button";
import type { VisaoOrdens } from "../types";

/** Um botão que mostra o destino da troca: "Ver em tabela" no Kanban, "Ver em Kanban" na tabela. */
export function VisaoToggle({
	value,
	onChange,
}: {
	value: VisaoOrdens;
	onChange: (v: VisaoOrdens) => void;
}) {
	const paraKanban = value === "tabela";
	const Icone = paraKanban ? KanbanIcon : TableIcon;

	return (
		<Button
			variant="outline"
			size="sm"
			onClick={() => onChange(paraKanban ? "kanban" : "tabela")}
		>
			<Icone aria-hidden />
			{paraKanban ? "Ver em Kanban" : "Ver em tabela"}
		</Button>
	);
}
