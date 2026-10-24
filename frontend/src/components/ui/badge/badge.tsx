// Badge do shadcn/ui (`npx shadcn@latest add badge`, estilo base-nova sobre Base UI) com
// visual de label, nos tokens da marca VE-360:
// - pílula de 24px, texto `text-small`, ícone de 14px;
// - a cor fica no ponto/ícone (`data-icon`), o texto continua neutro: o badge não
//   compete com o accent nem vira "bloco colorido" na tabela;
// - `outline` é o padrão (label); `secondary` é o preenchido (iniciativa).
// Outro elemento (link): `render={<a href="…" />}`.
import { mergeProps } from "@base-ui/react/merge-props";
import { useRender } from "@base-ui/react/use-render";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "#/lib/utils";

const badgeVariants = cva(
	"group/badge inline-flex h-6 w-fit shrink-0 items-center justify-center gap-1.5 overflow-hidden whitespace-nowrap rounded-full border border-transparent px-2.5 text-small text-text outline-none transition-colors focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2 aria-invalid:border-danger [&>svg]:pointer-events-none [&>svg]:size-3.5 [&>svg]:shrink-0",
	{
		variants: {
			variant: {
				outline: "border-border-strong [a]:hover:bg-hover",
				secondary: "bg-surface-2 [a]:hover:border-border-strong",
				ghost: "[a]:hover:bg-hover",
				destructive: "bg-danger-subtle text-danger",
				link: "text-info underline-offset-4 [a]:hover:underline",
			},
		},
		defaultVariants: {
			variant: "outline",
		},
	},
);

function Badge({
	className,
	variant = "outline",
	render,
	...props
}: Omit<useRender.ComponentProps<"span">, "className"> &
	VariantProps<typeof badgeVariants> & { className?: string }) {
	return useRender({
		defaultTagName: "span",
		props: mergeProps<"span">(
			{ className: cn(badgeVariants({ variant }), className) },
			props,
		),
		render,
		state: { slot: "badge", variant },
	});
}

export { Badge, badgeVariants };
