import { CaretDownIcon } from "@phosphor-icons/react";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuLabel,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuTrigger,
} from "#/components/ui/dropdown-menu";
import { formatPeriodo } from "#/lib/format";
import type { ParPeriodos } from "../types";

const chave = (p: ParPeriodos) => `${p.periodo_base}|${p.periodo_atual}`;
const rotulo = (p: ParPeriodos) =>
	`${formatPeriodo(p.periodo_base)} → ${formatPeriodo(p.periodo_atual)}`;

/** Só oferece os pares que a Gold gravou (DEC-028). */
export function PeriodoMenu({
	pares,
	par,
	onEscolher,
}: {
	pares: ParPeriodos[];
	par: ParPeriodos | undefined;
	onEscolher: (par: ParPeriodos) => void;
}) {
	const atual = par ? rotulo(par) : "Carregando…";
	return (
		<DropdownMenu>
			<DropdownMenuTrigger
				aria-label={`Períodos comparados: ${atual}. Trocar`}
				disabled={!par}
				className="flex h-7 min-w-0 cursor-pointer items-center gap-1 rounded-md px-1.5 text-small text-text-muted outline-none transition-colors hover:bg-hover focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover"
			>
				<span className="truncate">{atual}</span>
				<CaretDownIcon aria-hidden className="size-3 shrink-0" />
			</DropdownMenuTrigger>
			<DropdownMenuContent>
				<DropdownMenuRadioGroup
					value={par ? chave(par) : ""}
					onValueChange={(next: string) => {
						const escolhido = pares.find((p) => chave(p) === next);
						if (escolhido) onEscolher(escolhido);
					}}
				>
					<DropdownMenuGroup>
						<DropdownMenuLabel>Base → atual</DropdownMenuLabel>
						{pares.map((p) => (
							<DropdownMenuRadioItem key={chave(p)} value={chave(p)}>
								{rotulo(p)}
							</DropdownMenuRadioItem>
						))}
					</DropdownMenuGroup>
				</DropdownMenuRadioGroup>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
