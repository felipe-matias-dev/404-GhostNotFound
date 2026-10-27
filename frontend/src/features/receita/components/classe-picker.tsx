import { CaretDownIcon, FunnelSimpleIcon } from "@phosphor-icons/react";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuLabel,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "#/components/ui/dropdown-menu";
import { cn } from "#/lib/utils";
import { CLASSE_ROTULO, CLASSES } from "../conversions";
import type { Classe } from "../types";

const TODAS = "";

/** Filtro de classe de consumo: vale em todos os níveis do drill-down. */
export function ClassePicker({
	classe,
	onEscolher,
}: {
	classe: Classe | undefined;
	onEscolher: (classe: Classe | undefined) => void;
}) {
	return (
		<DropdownMenu>
			<DropdownMenuTrigger
				aria-label={`Classe de consumo: ${classe ? `${classe} ${CLASSE_ROTULO[classe]}` : "todas"}. Trocar`}
				className={cn(
					"flex h-7 min-w-0 cursor-pointer items-center gap-1.5 rounded-md border px-2 text-small outline-none transition-colors hover:bg-hover hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover data-popup-open:text-text",
					classe
						? "border-accent bg-accent-subtle text-accent-text"
						: "border-border text-text-muted",
				)}
			>
				<FunnelSimpleIcon aria-hidden className="size-3.5 shrink-0" />
				<span className="truncate">
					{classe ? `${classe} · ${CLASSE_ROTULO[classe]}` : "Todas as classes"}
				</span>
				<CaretDownIcon aria-hidden className="size-3 shrink-0" />
			</DropdownMenuTrigger>
			<DropdownMenuContent>
				<DropdownMenuRadioGroup
					value={classe ?? TODAS}
					onValueChange={(next: string) =>
						onEscolher(CLASSES.find((c) => c === next))
					}
				>
					<DropdownMenuRadioItem value={TODAS} closeOnClick>
						Todas as classes
					</DropdownMenuRadioItem>
					<DropdownMenuSeparator />
					<DropdownMenuGroup>
						<DropdownMenuLabel>Classe de consumo</DropdownMenuLabel>
						{CLASSES.map((c) => (
							<DropdownMenuRadioItem key={c} value={c} closeOnClick>
								<span className="inline-block w-6 font-medium tabular-nums">
									{c}
								</span>{" "}
								{CLASSE_ROTULO[c]}
							</DropdownMenuRadioItem>
						))}
					</DropdownMenuGroup>
				</DropdownMenuRadioGroup>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
