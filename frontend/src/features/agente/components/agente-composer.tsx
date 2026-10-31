import { ArrowUpIcon, CaretDownIcon } from "@phosphor-icons/react";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { LogoMark } from "#/components/layout/logo";
import { Button } from "#/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuLabel,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuTrigger,
} from "#/components/ui/dropdown-menu";
import { cn } from "#/lib/utils";
import { ESCOPOS_AGENTE, MAX_PERGUNTA_CHARS } from "../conversions";
import type { EscopoSugestao } from "../types";

export interface AgenteComposerProps {
	onSubmit: (pergunta: string) => void;
	enviando: boolean;
	escopo: EscopoSugestao;
	onEscopoChange: (escopo: EscopoSugestao) => void;
	placeholder?: string;
	compacto?: boolean;
	autoFocus?: boolean;
}

const PLACEHOLDER_PADRAO =
	"Pergunte sobre consumo, faturamento, DEC/FEC ou atendimento…";

export function AgenteComposer({
	onSubmit,
	escopo,
	onEscopoChange,
	placeholder = PLACEHOLDER_PADRAO,
	compacto = false,
	autoFocus = false,
}: AgenteComposerProps) {
	const [valor, setValor] = useState("");
	const campoRef = useRef<HTMLTextAreaElement>(null);
	const acimaDoLimite = valor.length > MAX_PERGUNTA_CHARS;
	const podeEnviar = valor.trim().length > 0 && !acimaDoLimite;

	useEffect(() => {
		if (autoFocus) campoRef.current?.focus();
	}, [autoFocus]);

	function dispararEnvio() {
		if (!podeEnviar) return;
		const texto = valor;
		setValor("");
		onSubmit(texto);
	}

	function aoTeclar(evento: KeyboardEvent<HTMLTextAreaElement>) {
		if (evento.key !== "Enter" || evento.shiftKey) return;
		if (evento.nativeEvent.isComposing) return;
		evento.preventDefault();
		dispararEnvio();
	}
	return (
		<div className="rounded-lg border border-border-strong bg-surface-1 shadow-edge transition-colors focus-within:border-focus-ring focus-within:ring-3 focus-within:ring-focus-ring/50">
			<textarea
				ref={campoRef}
				value={valor}
				onChange={(evento) => setValor(evento.target.value)}
				onKeyDown={aoTeclar}
				rows={compacto ? 2 : 3}
				placeholder={placeholder}
				aria-label="Pergunta para o agente"
				className="w-full resize-none bg-transparent px-3.5 pt-3 pb-1 text-body text-text outline-none placeholder:text-text-muted focus-visible:shadow-none focus-visible:outline-none"
			/>
			<div className="flex items-center justify-between gap-2 px-2.5 pt-1 pb-2.5">
				<DropdownMenu>
					<DropdownMenuTrigger
						type="button"
						className="inline-flex h-6 cursor-pointer items-center gap-1 rounded-md px-2 text-small font-medium text-text-muted outline-none transition-colors hover:bg-hover hover:text-text focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover data-popup-open:text-text"
					>
						<LogoMark className="size-3.5 text-accent-text" />
						<span className="truncate">{escopo}</span>
						<CaretDownIcon aria-hidden className="size-3" />
					</DropdownMenuTrigger>
					<DropdownMenuContent>
						<DropdownMenuGroup>
							<DropdownMenuLabel>Escopo de sugestões</DropdownMenuLabel>
							<DropdownMenuRadioGroup
								value={escopo}
								onValueChange={(valorEscolhido) =>
									onEscopoChange(valorEscolhido as EscopoSugestao)
								}
							>
								{ESCOPOS_AGENTE.map((opcao) => (
									<DropdownMenuRadioItem key={opcao} value={opcao}>
										{opcao}
									</DropdownMenuRadioItem>
								))}
							</DropdownMenuRadioGroup>
						</DropdownMenuGroup>
					</DropdownMenuContent>
				</DropdownMenu>
				<div className="flex items-center gap-2">
					{valor.length > 0 && (
						<span
							className={cn(
								"font-mono text-small tabular-nums",
								acimaDoLimite ? "text-danger" : "text-text-muted",
							)}
						>
							{valor.length}/{MAX_PERGUNTA_CHARS}
						</span>
					)}
					<Button
						type="button"
						size="icon-xs"
						className="rounded-full"
						disabled={!valor.trim() || acimaDoLimite}
						aria-label="Enviar pergunta"
						onClick={dispararEnvio}
					>
						<ArrowUpIcon aria-hidden weight="bold" className="size-3.5" />
					</Button>
				</div>
			</div>
		</div>
	);
}
