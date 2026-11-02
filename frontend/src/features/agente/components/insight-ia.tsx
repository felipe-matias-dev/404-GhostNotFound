// Insight de IA de uma tela, ao lado da frase de leitura que o texto aprofunda. O modelo só é
// chamado quando o usuário pede ("Gerar insight", com a marca do VE-360, o sinal de "feito
// pelo agente"); o texto chega aberto numa caixa, que fecha pelo X, por Esc ou clicando fora,
// e volta pelo botão "Insight feito por IA". Sem texto (narração descartada, falha do provedor
// ou IA desligada), a tela diz que o insight está indisponível, nunca mostra texto inventado.
import { XIcon } from "@phosphor-icons/react";
import { useState } from "react";
import { LogoMark } from "#/components/layout/logo";
import { Button, buttonVariants } from "#/components/ui/button";
import {
	Popover,
	PopoverClose,
	PopoverContent,
	PopoverTrigger,
} from "#/components/ui/popover";
import { cn } from "#/lib/utils";

const TITULO = "Insight feito por IA";

export function InsightIa({
	texto,
	carregando = false,
	indisponivel = false,
	onGerar,
	className,
}: {
	texto?: string | null;
	carregando?: boolean;
	/** Já houve tentativa e não veio texto. */
	indisponivel?: boolean;
	onGerar: () => void;
	className?: string;
}) {
	const [aberto, setAberto] = useState(false);
	// Quem clicou em "Gerar" quer ler: o texto abre assim que a busca pedida termina.
	const [pedido, setPedido] = useState<"nenhum" | "enviado" | "carregando">(
		"nenhum",
	);
	if (pedido === "enviado" && carregando) setPedido("carregando");
	if (pedido === "carregando" && !carregando) {
		setPedido("nenhum");
		setAberto(Boolean(texto));
	}

	const gerar = () => {
		setPedido("enviado");
		onGerar();
	};

	if (carregando) {
		return (
			<output
				className={cn(
					"inline-flex h-6 items-center gap-1.5 px-2 text-small text-text-muted",
					className,
				)}
			>
				<LogoMark className="size-3.5 text-accent-text motion-safe:animate-pulse" />
				Gerando insight…
			</output>
		);
	}
	if (texto) {
		return (
			<Popover open={aberto} onOpenChange={setAberto}>
				<PopoverTrigger
					className={cn(
						buttonVariants({ variant: "outline", size: "xs" }),
						"data-popup-open:bg-hover",
						className,
					)}
				>
					<LogoMark className="size-3.5 text-accent-text" />
					{TITULO}
				</PopoverTrigger>
				<PopoverContent
					align="end"
					aria-label={TITULO}
					className="flex w-[min(28rem,calc(100vw-1.5rem))] flex-col gap-3 p-4"
				>
					<div className="flex items-center gap-2">
						<LogoMark className="size-4 text-accent-text" />
						<p className="font-medium text-body text-text">{TITULO}</p>
						<PopoverClose
							aria-label="Fechar insight"
							className={cn(
								buttonVariants({ variant: "ghost", size: "icon-xs" }),
								"-mr-1.5 ml-auto text-text-muted hover:text-text",
							)}
						>
							<XIcon aria-hidden />
						</PopoverClose>
					</div>
					<p className="text-body text-text">{texto}</p>
					<p className="border-t border-border pt-3 text-small text-text-muted">
						Gerado por IA a partir das métricas desta tela. Todo número do texto
						foi conferido com elas.
					</p>
				</PopoverContent>
			</Popover>
		);
	}
	if (indisponivel) {
		return (
			<div
				className={cn(
					"inline-flex items-center gap-1 text-small text-text-muted",
					className,
				)}
			>
				<output>Insight indisponível.</output>
				<Button variant="ghost" size="xs" onClick={gerar}>
					Tentar de novo
				</Button>
			</div>
		);
	}
	return (
		<Button variant="outline" size="xs" onClick={gerar} className={className}>
			<LogoMark className="size-3.5 text-accent-text" />
			Gerar insight
		</Button>
	);
}
