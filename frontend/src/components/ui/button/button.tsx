// Button do shadcn/ui (`npx shadcn@latest add button`) adaptado aos tokens da marca VE-360:
// - cores só por tokens semânticos (accent, danger, hover/pressed…);
// - foco igual ao do shadcn (borda + anel de 3px a 50%), na cor `focus-ring`;
// - desabilitado vira surface-2 + text-disabled em qualquer variante, sem opacidade;
// - sem sombra: o amarelo já é o destaque.
import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import type * as React from "react";
import { cn } from "#/lib/utils";

const buttonVariants = cva(
	"inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium text-body outline-none transition-all focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 disabled:pointer-events-none disabled:border disabled:border-border disabled:bg-surface-2 disabled:text-text-disabled aria-invalid:border-danger aria-invalid:ring-danger/20 [&_svg:not([class*='size-'])]:size-4 [&_svg]:pointer-events-none [&_svg]:shrink-0",
	{
		variants: {
			variant: {
				default: "bg-accent text-on-accent hover:bg-accent-hover",
				destructive: "bg-danger text-on-danger hover:bg-danger-hover",
				outline:
					"border border-border-strong text-text hover:bg-hover active:bg-pressed",
				secondary:
					"border border-border bg-surface-2 text-text hover:border-border-strong",
				ghost: "text-text hover:bg-hover active:bg-pressed",
				link: "text-info underline-offset-4 hover:underline",
			},
			size: {
				default: "h-9 px-4 py-2 has-[>svg]:px-3",
				xs: "h-6 gap-1 px-2 text-small has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
				sm: "h-8 gap-1.5 px-3 has-[>svg]:px-2.5",
				lg: "h-10 px-6 has-[>svg]:px-4",
				icon: "size-9",
				"icon-xs": "size-6 [&_svg:not([class*='size-'])]:size-3",
				"icon-sm": "size-8",
				"icon-lg": "size-10",
			},
		},
		defaultVariants: {
			variant: "default",
			size: "default",
		},
	},
);

function Button({
	className,
	variant = "default",
	size = "default",
	asChild = false,
	...props
}: React.ComponentProps<"button"> &
	VariantProps<typeof buttonVariants> & {
		asChild?: boolean;
	}) {
	const Comp = asChild ? Slot.Root : "button";

	return (
		<Comp
			data-slot="button"
			data-variant={variant}
			data-size={size}
			className={cn(buttonVariants({ variant, size, className }))}
			{...props}
		/>
	);
}

export { Button, buttonVariants };
