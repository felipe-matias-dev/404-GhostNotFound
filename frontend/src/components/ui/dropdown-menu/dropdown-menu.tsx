// DropdownMenu do shadcn/ui (`npx shadcn@latest add dropdown-menu`, estilo base-nova sobre
// Base UI) adaptado aos tokens da marca VE-360:
// - flutua: surface-2 + border-strong + shadow-overlay (Fundamentos/Elevação);
// - item em `text-body`, foco/hover em `hover`, marcado com check em `accent-text`;
// - entrada/saída por opacidade e escala com os estados do Base UI, sem tw-animate-css;
// - só as partes usadas no portal: grupo, rótulo, item, item de rádio e separador.
import { Menu as MenuPrimitive } from "@base-ui/react/menu";
import { CheckIcon } from "@phosphor-icons/react";
import { cn } from "#/lib/utils";

const ITEM =
	"relative flex min-h-8 cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-body text-text outline-none data-disabled:pointer-events-none data-highlighted:bg-hover data-disabled:text-text-disabled [&_svg:not([class*='size-'])]:size-4 [&_svg]:pointer-events-none [&_svg]:shrink-0";

function DropdownMenu({ ...props }: MenuPrimitive.Root.Props) {
	return <MenuPrimitive.Root data-slot="dropdown-menu" {...props} />;
}

function DropdownMenuTrigger({ ...props }: MenuPrimitive.Trigger.Props) {
	return <MenuPrimitive.Trigger data-slot="dropdown-menu-trigger" {...props} />;
}

function DropdownMenuContent({
	align = "start",
	alignOffset = 0,
	side = "bottom",
	sideOffset = 6,
	className,
	...props
}: Omit<MenuPrimitive.Popup.Props, "className"> & {
	className?: string;
} & Pick<
		MenuPrimitive.Positioner.Props,
		"align" | "alignOffset" | "side" | "sideOffset"
	>) {
	return (
		<MenuPrimitive.Portal>
			<MenuPrimitive.Positioner
				className="isolate z-50 outline-none"
				align={align}
				alignOffset={alignOffset}
				side={side}
				sideOffset={sideOffset}
			>
				<MenuPrimitive.Popup
					data-slot="dropdown-menu-content"
					className={cn(
						"z-50 max-h-[min(var(--available-height),24rem)] min-w-48 origin-(--transform-origin) overflow-y-auto overscroll-contain rounded-md border border-border-strong bg-surface-2 p-1 text-text shadow-overlay outline-none transition-[opacity,scale] duration-150 data-ending-style:scale-95 data-starting-style:scale-95 data-ending-style:opacity-0 data-starting-style:opacity-0 motion-reduce:transition-none",
						className,
					)}
					{...props}
				/>
			</MenuPrimitive.Positioner>
		</MenuPrimitive.Portal>
	);
}

function DropdownMenuGroup({ ...props }: MenuPrimitive.Group.Props) {
	return <MenuPrimitive.Group data-slot="dropdown-menu-group" {...props} />;
}

function DropdownMenuLabel({
	className,
	...props
}: Omit<MenuPrimitive.GroupLabel.Props, "className"> & { className?: string }) {
	return (
		<MenuPrimitive.GroupLabel
			data-slot="dropdown-menu-label"
			className={cn("px-2 pt-1.5 pb-1 text-small text-text-muted", className)}
			{...props}
		/>
	);
}

function DropdownMenuItem({
	className,
	...props
}: Omit<MenuPrimitive.Item.Props, "className"> & { className?: string }) {
	return (
		<MenuPrimitive.Item
			data-slot="dropdown-menu-item"
			className={cn(ITEM, className)}
			{...props}
		/>
	);
}

function DropdownMenuRadioGroup({ ...props }: MenuPrimitive.RadioGroup.Props) {
	return (
		<MenuPrimitive.RadioGroup
			data-slot="dropdown-menu-radio-group"
			{...props}
		/>
	);
}

function DropdownMenuRadioItem({
	className,
	children,
	...props
}: Omit<MenuPrimitive.RadioItem.Props, "className"> & { className?: string }) {
	return (
		<MenuPrimitive.RadioItem
			data-slot="dropdown-menu-radio-item"
			className={cn(ITEM, "pr-8", className)}
			{...props}
		>
			<span className="min-w-0 flex-1 truncate">{children}</span>
			<span className="pointer-events-none absolute right-2 flex items-center">
				<MenuPrimitive.RadioItemIndicator>
					<CheckIcon aria-hidden className="text-accent-text" />
				</MenuPrimitive.RadioItemIndicator>
			</span>
		</MenuPrimitive.RadioItem>
	);
}

function DropdownMenuSeparator({
	className,
	...props
}: Omit<MenuPrimitive.Separator.Props, "className"> & { className?: string }) {
	return (
		<MenuPrimitive.Separator
			data-slot="dropdown-menu-separator"
			className={cn("-mx-1 my-1 h-px bg-border", className)}
			{...props}
		/>
	);
}

export {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
};
