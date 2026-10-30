import { CaretDownIcon } from "@phosphor-icons/react";
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

const TODOS = "";

export function NivelMenu({
	nivel,
	todos,
	valor,
	opcoes,
	carregando,
	erro,
	atual,
	onEscolher,
}: {
	nivel: string;
	todos: string;
	valor: string | undefined;
	opcoes: string[];
	carregando: boolean;
	/** O catálogo falhou: é diferente de não ter opções. */
	erro?: boolean;
	/** Último nível da trilha: é o recorte que a página mostra. */
	atual: boolean;
	onEscolher: (valor: string | undefined) => void;
}) {
	const rotulo = valor ?? todos;
	return (
		<DropdownMenu>
			<DropdownMenuTrigger
				aria-label={`${nivel}: ${rotulo}. Trocar`}
				className={cn(
					"flex h-8 min-w-0 cursor-pointer items-center gap-1.5 rounded-md border px-2 text-small outline-none transition-colors hover:bg-hover hover:text-text focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover data-popup-open:text-text",
					valor
						? "border-accent bg-accent-subtle text-accent-text"
						: "border-border-strong text-text-muted",
				)}
			>
				<span className="truncate" aria-current={atual ? "page" : undefined}>
					{rotulo}
				</span>
				<CaretDownIcon
					aria-hidden
					className="size-3 shrink-0 text-text-muted"
				/>
			</DropdownMenuTrigger>
			<DropdownMenuContent>
				<DropdownMenuRadioGroup
					value={valor ?? TODOS}
					onValueChange={(next: string) => onEscolher(next || undefined)}
				>
					<DropdownMenuRadioItem value={TODOS}>{todos}</DropdownMenuRadioItem>
					<DropdownMenuSeparator />
					<DropdownMenuGroup>
						<DropdownMenuLabel>
							{carregando
								? "Carregando…"
								: erro
									? "Falha ao carregar"
									: opcoes.length
										? nivel
										: "Nenhuma opção disponível"}
						</DropdownMenuLabel>
						{opcoes.map((opcao) => (
							<DropdownMenuRadioItem key={opcao} value={opcao}>
								{opcao}
							</DropdownMenuRadioItem>
						))}
					</DropdownMenuGroup>
				</DropdownMenuRadioGroup>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
