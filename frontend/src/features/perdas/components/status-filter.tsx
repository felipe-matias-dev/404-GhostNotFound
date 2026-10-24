import { Button } from "#/components/ui/button";
import { STATUS_ORDEM_VISUAL } from "../conversions";
import { STATUS_ORDEM, type StatusOrdem } from "../types";

const OPCOES: { valor: StatusOrdem | undefined; rotulo: string }[] = [
	{ valor: undefined, rotulo: "Todas" },
	...STATUS_ORDEM.map((valor) => ({
		valor,
		rotulo: STATUS_ORDEM_VISUAL[valor].rotulo,
	})),
];

export function StatusFilter({
	value,
	onChange,
}: {
	value: StatusOrdem | undefined;
	onChange: (next: StatusOrdem | undefined) => void;
}) {
	return (
		// biome-ignore lint/a11y/useSemanticElements: grupo de botões de filtro, não formulário.
		<div
			role="group"
			aria-label="Filtrar por status"
			className="-mx-1 flex gap-1 overflow-x-auto px-1 py-1"
		>
			{OPCOES.map(({ valor, rotulo }) => (
				<Button
					key={rotulo}
					size="sm"
					variant={value === valor ? "secondary" : "ghost"}
					aria-pressed={value === valor}
					onClick={() => onChange(valor)}
					className={value === valor ? undefined : "text-text-muted"}
				>
					{rotulo}
				</Button>
			))}
		</div>
	);
}
