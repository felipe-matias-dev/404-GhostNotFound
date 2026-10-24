import { PlusIcon } from "@phosphor-icons/react";
import { type FormEvent, useId, useRef, useState } from "react";
import { Button } from "#/components/ui/button";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetFooter,
	SheetHeader,
	SheetTitle,
	SheetTrigger,
} from "#/components/ui/sheet";
import { lerCodigosUc, mensagemErroOrdem } from "../conversions";
import { useCriarOrdens } from "../hooks/use-criar-ordens";
import { MAX_ORDENS_POR_PEDIDO } from "../types";

function rotuloEnvio(quantidade: number) {
	if (quantidade === 0) return "Gerar OIs";
	if (quantidade === 1) return "Gerar OI";
	return `Gerar ${quantidade} OIs`;
}

function rotuloSucesso(quantidade: number) {
	return quantidade === 1 ? "1 OI gerada." : `${quantidade} OIs geradas.`;
}

export function GerarOrdens() {
	const id = useId();
	const idTexto = `${id}-ucs`;
	const idDica = `${id}-dica`;
	const idErroCampo = `${id}-erro-campo`;

	const [aberto, setAberto] = useState(false);
	const [texto, setTexto] = useState("");
	const [erroCampo, setErroCampo] = useState<string | null>(null);
	const [erroApi, setErroApi] = useState<string | null>(null);
	const [anuncio, setAnuncio] = useState("");
	const textareaRef = useRef<HTMLTextAreaElement>(null);
	const criar = useCriarOrdens();

	const { codigos, repetidos } = lerCodigosUc(texto);
	const quantidade = codigos.length;

	const dica =
		quantidade === 0
			? "Separe por vírgula, espaço ou linha."
			: `${quantidade} ${quantidade === 1 ? "UC" : "UCs"}${
					repetidos > 0
						? ` · ${repetidos} ${repetidos === 1 ? "repetida ignorada" : "repetidas ignoradas"}`
						: ""
				}`;

	function aoMudarTexto(valor: string) {
		setTexto(valor);
		setErroCampo(null);
		setErroApi(null);
	}

	function aoEnviar(evento: FormEvent<HTMLFormElement>) {
		evento.preventDefault();
		setErroApi(null);

		if (quantidade === 0) {
			setErroCampo("Informe ao menos uma UC.");
			textareaRef.current?.focus();
			return;
		}
		if (quantidade > MAX_ORDENS_POR_PEDIDO) {
			setErroCampo(
				`No máximo ${MAX_ORDENS_POR_PEDIDO} UCs por pedido (você informou ${quantidade}).`,
			);
			textareaRef.current?.focus();
			return;
		}

		setErroCampo(null);
		criar.mutate(codigos, {
			onSuccess: (ordens) => {
				setAberto(false);
				setTexto("");
				setErroApi(null);
				setAnuncio(rotuloSucesso(ordens.length));
			},
			onError: (error) => {
				setErroApi(mensagemErroOrdem(error, "Não foi possível gerar as OIs."));
			},
		});
	}

	return (
		<>
			<Sheet open={aberto} onOpenChange={setAberto}>
				<SheetTrigger render={<Button variant="default" size="sm" />}>
					<PlusIcon aria-hidden />
					Gerar OIs
				</SheetTrigger>
				<SheetContent side="right">
					<SheetHeader>
						<SheetTitle>Gerar ordens de inspeção</SheetTitle>
						<SheetDescription>
							Uma OI por unidade consumidora, até 200 por pedido. Se alguma UC
							não existir ou já tiver OI ativa, nenhuma OI é gerada.
						</SheetDescription>
					</SheetHeader>
					<form
						onSubmit={aoEnviar}
						className="flex min-h-0 flex-1 flex-col gap-3 px-4"
					>
						<div className="flex flex-col gap-1.5">
							<label htmlFor={idTexto} className="text-small text-text">
								Códigos das UCs
							</label>
							<textarea
								id={idTexto}
								ref={textareaRef}
								rows={6}
								value={texto}
								onChange={(evento) => aoMudarTexto(evento.target.value)}
								placeholder="0001, 0002 ou um por linha"
								aria-invalid={erroCampo ? true : undefined}
								aria-describedby={
									erroCampo ? `${idDica} ${idErroCampo}` : idDica
								}
								className="resize-y rounded-md border border-border bg-surface-1 px-3 py-2 font-mono text-code text-text outline-none placeholder:text-text-muted focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 aria-invalid:border-danger"
							/>
							<p id={idDica} className="text-small text-text-muted">
								{dica}
							</p>
							{erroCampo && (
								<p id={idErroCampo} className="text-small text-danger">
									{erroCampo}
								</p>
							)}
						</div>
						{erroApi && (
							<p
								role="alert"
								className="rounded-md border border-danger bg-danger-subtle px-3 py-2 text-small text-text"
							>
								{erroApi}
							</p>
						)}
						<SheetFooter className="flex-row justify-end gap-2 px-0 pb-4 pt-3">
							<Button
								type="button"
								variant="ghost"
								onClick={() => setAberto(false)}
							>
								Voltar
							</Button>
							<Button type="submit" disabled={criar.isPending}>
								{criar.isPending ? "Gerando…" : rotuloEnvio(quantidade)}
							</Button>
						</SheetFooter>
					</form>
				</SheetContent>
			</Sheet>
			<output aria-live="polite" className="sr-only">
				{anuncio}
			</output>
		</>
	);
}
