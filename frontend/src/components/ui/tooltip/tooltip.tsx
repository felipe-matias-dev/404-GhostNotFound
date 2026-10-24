// Tooltip do shadcn/ui (`npx shadcn@latest add tooltip`, estilo base-nova sobre Base UI)
// adaptado aos tokens da marca VE-360:
// - flutua: surface-2 + border-strong + shadow-overlay (Fundamentos/Elevação);
// - texto `text-small`, sem seta;
// - entrada/saída por opacidade com os estados do Base UI, sem tw-animate-css.
import { Tooltip as TooltipPrimitive } from "@base-ui/react/tooltip";
import { cn } from "#/lib/utils";

function TooltipProvider({
	delay = 0,
	...props
}: TooltipPrimitive.Provider.Props) {
	return (
		<TooltipPrimitive.Provider
			data-slot="tooltip-provider"
			delay={delay}
			{...props}
		/>
	);
}

function Tooltip({ ...props }: TooltipPrimitive.Root.Props) {
	return <TooltipPrimitive.Root data-slot="tooltip" {...props} />;
}

function TooltipTrigger({ ...props }: TooltipPrimitive.Trigger.Props) {
	return <TooltipPrimitive.Trigger data-slot="tooltip-trigger" {...props} />;
}

function TooltipContent({
	className,
	side = "top",
	sideOffset = 6,
	align = "center",
	alignOffset = 0,
	children,
	...props
}: Omit<TooltipPrimitive.Popup.Props, "className"> & {
	className?: string;
} & Pick<
		TooltipPrimitive.Positioner.Props,
		"align" | "alignOffset" | "side" | "sideOffset"
	>) {
	return (
		<TooltipPrimitive.Portal>
			<TooltipPrimitive.Positioner
				align={align}
				alignOffset={alignOffset}
				side={side}
				sideOffset={sideOffset}
				className="isolate z-50"
			>
				<TooltipPrimitive.Popup
					data-slot="tooltip-content"
					className={cn(
						"z-50 inline-flex w-fit max-w-xs origin-(--transform-origin) items-center gap-1.5 rounded-md border border-border-strong bg-surface-2 px-2 py-1 text-small text-text shadow-overlay transition-opacity duration-150 data-ending-style:opacity-0 data-starting-style:opacity-0 motion-reduce:transition-none",
						className,
					)}
					{...props}
				>
					{children}
				</TooltipPrimitive.Popup>
			</TooltipPrimitive.Positioner>
		</TooltipPrimitive.Portal>
	);
}

export { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger };
