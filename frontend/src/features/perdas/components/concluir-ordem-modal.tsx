import { type FormEvent, useEffect, useId, useRef, useState } from "react";
import { Button } from "#/components/ui/button";
import { FloatingLabelTextarea } from "#/components/ui/floating-label";
import { Modal } from "#/components/ui/modal";
import { mensagemErroOrdem, RESULTADO_ORDEM_ROTULO } from "../conversions";
import {
	type AtualizarOrdem,
	type Ordem,
	RESULTADO_ORDEM,
	type ResultadoOrdem,
} from "../types";

export function ConcluirOrdemModal({
	ordem,
	open,
	onOpenChange,
	onConcluida,
	onEnviar,
}: {
	ordem: Ordem | null;
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onConcluida: (ordem: Ordem) => void;
	onEnviar: (ordem: Ordem, mudanca: AtualizarOrdem) => Promise<void>;
}) {
	const [resultado, setResultado] = useState<ResultadoOrdem | null>(null);
	const [observacao, setObservacao] = useState("");
	const [erroCampo, setErroCampo] = useState(false);
	const [erroApi, setErroApi] = useState<string | null>(null);
	const [enviando, setEnviando] = useState(false);
	const primeiroRadio = useRef<HTMLInputElement>(null);

	const idFormulario = useId();
	const idResultado = useId();
	const idErroCampo = useId();

	useEffect(() => {
		if (!open) return;
		setResultado(null);
		setObservacao("");
		setErroCampo(false);
		setErroApi(null);
		setEnviando(false);
	}, [open]);

	const aoEnviar = async (event: FormEvent<HTMLFormElement>) => {
		event.preventDefault();
		if (!ordem || enviando) return;
		if (!resultado) {
			setErroCampo(true);
			primeiroRadio.current?.focus();
			return;
		}
		setErroCampo(false);
		setErroApi(null);
		setEnviando(true);
		try {
			await onEnviar(ordem, {
				status: "CONCLUIDA",
				resultado,
				observacao: observacao.trim() || undefined,
			});
			onConcluida(ordem);
		} catch (error) {
			setErroApi(
				mensagemErroOrdem(
					error,
					`Não foi possível concluir a OI #${ordem.id}.`,
				),
			);
		} finally {
			setEnviando(false);
		}
	};

	return (
		<Modal
			open={open}
			onClose={() => onOpenChange(false)}
			// Durante o PATCH o modal não fecha: o resultado do pedido aparece nele.
			closeOnEscape={!enviando}
			closeOnBackdrop={!enviando}
			initialFocusRef={primeiroRadio}
			title={`Concluir OI #${ordem?.id}`}
			description={`UC ${ordem?.cod_uc} · registre o que a equipe encontrou em campo.`}
			footer={
				<>
					<Button
						type="button"
						variant="ghost"
						disabled={enviando}
						onClick={() => onOpenChange(false)}
					>
						Voltar
					</Button>
					<Button type="submit" form={idFormulario} disabled={enviando}>
						{enviando ? "Concluindo…" : "Concluir OI"}
					</Button>
				</>
			}
		>
			<form
				id={idFormulario}
				onSubmit={aoEnviar}
				className="flex flex-col gap-4"
			>
				<fieldset
					aria-invalid={erroCampo || undefined}
					aria-describedby={erroCampo ? idErroCampo : undefined}
					className="flex flex-col gap-2"
				>
					<legend className="mb-1 text-small text-text-muted">
						Resultado da inspeção
					</legend>
					{RESULTADO_ORDEM.map((valor, indice) => (
						<label
							key={valor}
							className="flex items-center gap-2 text-body text-text"
						>
							<input
								ref={indice === 0 ? primeiroRadio : undefined}
								type="radio"
								name={idResultado}
								value={valor}
								checked={resultado === valor}
								onChange={() => {
									setResultado(valor);
									setErroCampo(false);
								}}
								className="size-4 accent-accent"
							/>
							{RESULTADO_ORDEM_ROTULO[valor]}
						</label>
					))}
				</fieldset>
				{erroCampo && (
					<p id={idErroCampo} className="-mt-2 text-body text-danger">
						Escolha o resultado da inspeção.
					</p>
				)}
				<FloatingLabelTextarea
					label="Observação (opcional)"
					value={observacao}
					onChange={setObservacao}
					maxLength={1000}
					rows={4}
				/>
				{erroApi && (
					<p
						role="alert"
						className="rounded-md bg-danger-subtle px-3 py-2 text-body text-danger"
					>
						{erroApi}
					</p>
				)}
			</form>
		</Modal>
	);
}
