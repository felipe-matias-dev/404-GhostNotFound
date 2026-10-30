import { Checkbox as CheckboxPrimitive } from "@base-ui/react/checkbox";
import { CheckIcon, MinusIcon } from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { cn } from "#/lib/utils";

const SPRING = {
	type: "spring",
	stiffness: 520,
	damping: 34,
	mass: 0.45,
} as const;

export function Checkbox({
	id,
	checked,
	indeterminate = false,
	onChange,
	label,
	disabled = false,
	className,
}: {
	id?: string;
	checked: boolean;
	indeterminate?: boolean;
	onChange: (checked: boolean) => void;
	label: string;
	disabled?: boolean;
	className?: string;
}) {
	const reduced = useReducedMotion();
	const on = checked || indeterminate;
	return (
		<CheckboxPrimitive.Root
			id={id}
			checked={checked}
			disabled={disabled}
			indeterminate={indeterminate}
			onCheckedChange={(next) => onChange(next)}
			aria-label={label}
			onClick={(event) => event.stopPropagation()}
			className={cn(
				"relative z-10 grid size-4 shrink-0 cursor-pointer place-items-center rounded-sm border outline-none transition-colors duration-150 focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50",
				on
					? "border-accent bg-accent text-on-accent"
					: "border-border-strong text-transparent hover:bg-hover",
				disabled && "cursor-not-allowed border-border bg-surface-2",
				disabled && on && "text-text-disabled",
				className,
			)}
		>
			<motion.span
				aria-hidden
				className="flex"
				initial={false}
				animate={{ scale: on ? 1 : 0.4 }}
				transition={reduced ? { duration: 0 } : SPRING}
			>
				{indeterminate ? (
					<MinusIcon weight="bold" className="size-3" />
				) : (
					<CheckIcon weight="bold" className="size-3" />
				)}
			</motion.span>
		</CheckboxPrimitive.Root>
	);
}
