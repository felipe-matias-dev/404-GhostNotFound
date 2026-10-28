// Controle segmentado: escolha única entre poucas opções curtas (visão, escala, unidade).
// Base UI ToggleGroup (setas percorrem, `aria-pressed` no escolhido) com os tokens VE-360:
// - trilho em `bg` com `border`; o escolhido ganha uma pílula `surface-2` que desliza até ele
//   (mola; com movimento reduzido, troca seca);
// - texto `text-small`: `text-muted` em repouso, `text` no hover e no escolhido;
// - clicar no escolhido não o desmarca: sempre há uma opção valendo.
// Mais de quatro opções ou rótulos longos pedem um DropdownMenu.
import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import { motion, useReducedMotion } from "motion/react";
import { type ReactNode, useId } from "react";
import { cn } from "#/lib/utils";

const SPRING = {
	type: "spring",
	stiffness: 420,
	damping: 36,
	mass: 0.7,
} as const;

export type SegmentedOption<Value extends string> = {
	value: Value;
	label: ReactNode;
	/** Nome acessível quando o rótulo é só um ícone. */
	ariaLabel?: string;
};

export type SegmentedControlProps<Value extends string> = {
	/** Nome acessível do grupo: "Visão do gráfico". */
	label: string;
	value: Value;
	onValueChange: (value: Value) => void;
	options: readonly SegmentedOption<Value>[];
	disabled?: boolean;
	className?: string;
};

export function SegmentedControl<Value extends string>({
	label,
	value,
	onValueChange,
	options,
	disabled = false,
	className,
}: SegmentedControlProps<Value>) {
	const reduced = useReducedMotion();
	const pillId = useId();
	return (
		<ToggleGroup<Value>
			aria-label={label}
			value={[value]}
			onValueChange={(next) => {
				const [chosen] = next;
				if (chosen !== undefined && chosen !== value) onValueChange(chosen);
			}}
			disabled={disabled}
			className={cn(
				"inline-flex h-7 items-center gap-0.5 rounded-md border border-border bg-bg p-0.5",
				className,
			)}
		>
			{options.map((option) => {
				const pressed = option.value === value;
				return (
					<Toggle
						key={option.value}
						value={option.value}
						aria-label={option.ariaLabel}
						className="relative flex h-full cursor-pointer select-none items-center gap-1.5 whitespace-nowrap rounded-sm px-2 text-small text-text-muted outline-none transition-colors hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-disabled:pointer-events-none data-disabled:text-text-disabled data-pressed:text-text [&_svg:not([class*='size-'])]:size-3.5 [&_svg]:shrink-0"
					>
						{pressed ? (
							<motion.span
								aria-hidden
								layoutId={pillId}
								transition={reduced ? { duration: 0 } : SPRING}
								className="absolute inset-0 rounded-sm bg-surface-2 shadow-edge ring-1 ring-border-strong"
							/>
						) : null}
						<span className="relative flex items-center gap-1.5">
							{option.label}
						</span>
					</Toggle>
				);
			})}
		</ToggleGroup>
	);
}
