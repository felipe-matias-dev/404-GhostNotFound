// Popover do shadcn/ui (`npx shadcn@latest add popover`, estilo base-nova sobre Base UI)
// adaptado aos tokens da marca VE-360:
// - flutua como o DropdownMenu: surface-2 + border-strong + shadow-overlay;
// - entrada/saída por opacidade e escala com os estados do Base UI, sem tw-animate-css;
// - só as partes usadas no portal: raiz, gatilho, conteúdo e fechar.
import { Popover as PopoverPrimitive } from "@base-ui/react/popover";
import { cn } from "#/lib/utils";

function Popover({ ...props }: PopoverPrimitive.Root.Props) {
	return <PopoverPrimitive.Root data-slot="popover" {...props} />;
}

function PopoverTrigger({ ...props }: PopoverPrimitive.Trigger.Props) {
	return <PopoverPrimitive.Trigger data-slot="popover-trigger" {...props} />;
}

function PopoverClose({ ...props }: PopoverPrimitive.Close.Props) {
	return <PopoverPrimitive.Close data-slot="popover-close" {...props} />;
}

function PopoverContent({
	className,
	align = "start",
	alignOffset = 0,
	side = "bottom",
	sideOffset = 6,
	...props
}: Omit<PopoverPrimitive.Popup.Props, "className"> & {
	className?: string;
} & Pick<
		PopoverPrimitive.Positioner.Props,
		"align" | "alignOffset" | "side" | "sideOffset"
	>) {
	return (
		<PopoverPrimitive.Portal>
			<PopoverPrimitive.Positioner
				className="isolate z-50 outline-none"
				align={align}
				alignOffset={alignOffset}
				side={side}
				sideOffset={sideOffset}
			>
				<PopoverPrimitive.Popup
					data-slot="popover-content"
					className={cn(
						"z-50 origin-(--transform-origin) rounded-md border border-border-strong bg-surface-2 text-text shadow-overlay outline-none transition-[opacity,scale] duration-150 data-ending-style:scale-95 data-starting-style:scale-95 data-ending-style:opacity-0 data-starting-style:opacity-0 motion-reduce:transition-none",
						className,
					)}
					{...props}
				/>
			</PopoverPrimitive.Positioner>
		</PopoverPrimitive.Portal>
	);
}

export { Popover, PopoverClose, PopoverContent, PopoverTrigger };
