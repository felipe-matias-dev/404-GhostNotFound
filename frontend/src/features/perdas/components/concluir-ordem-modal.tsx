import { type FormEvent, useEffect, useId, useRef, useState } from "react";
import { Button } from "#/components/ui/button";
import { FloatingLabelTextarea } from "#/components/ui/floating-label";
import { Modal } from "#/components/ui/modal";
import {
	lerKwhRecuperado,
	mensagemErroOrdem,
	RESULTADO_ORDEM_ROTULO,
	TIPOS_IRREGULARIDADE,
} from "../conversions";
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
	const [tipo, setTipo] = useState("");
	const [kwh, setKwh] = useState("");
	const [erroCampo, setErroCampo] = useState(false);
	const [erroTipo, setErroTipo] = useState(false);
	const [erroKwh, setErroKwh] = useState(false);
	const [erroApi, setErroApi] = useState<string | null>(null);
	const [enviando, setEnviando] = useState(false);
	const primeiroRadio = useRef<HTMLInputElement>(null);

	const idFormulario = useId();
	const idResultado = useId();
	const idErroCampo = useId();
	const idTipo = useId();
	const idTipos = useId();
	const idKwh = useId();
	const idErroTipo = useId();
	const idErroKwh = useId();
	const irregular = resultado === "IRREGULAR_CONFIRMADA";

	useEffect(() => {
		if (!open) return;
		setResultado(null);
		setObservacao("");
		setTipo("");
		setKwh("");
		setErroCampo(false);
		setErroTipo(false);
		setErroKwh(false);
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
		const tipoLimpo = tipo.trim();
		const kwhLido = irregular ? lerKwhRecuperado(kwh) : null;
		if (irregular && (!tipoLimpo || kwhLido === null)) {
			setErroTipo(!tipoLimpo);
			setErroKwh(kwhLido === null);
			setErroApi(null);
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
				...(irregular
					? { tipo_irregularidade: tipoLimpo, kwh_recuperado: kwhLido }
					: {}),
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
									setErroTipo(false);
									setErroKwh(false);
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
				{irregular && (
					<div className="flex flex-col gap-4">
						<div className="flex flex-col gap-1">
							<label htmlFor={idTipo} className="text-small text-text-muted">
								Tipo de irregularidade
							</label>
							<input
								id={idTipo}
								type="text"
								list={idTipos}
								value={tipo}
								maxLength={100}
								onChange={(event) => {
									setTipo(event.target.value);
									setErroTipo(false);
								}}
								aria-invalid={erroTipo || undefined}
								aria-describedby={erroTipo ? idErroTipo : undefined}
								className="h-10 w-full rounded-md border border-border bg-transparent px-3 text-body text-text outline-none focus-visible:ring-2 focus-visible:ring-focus-ring aria-invalid:border-danger"
							/>
							<datalist id={idTipos}>
								{TIPOS_IRREGULARIDADE.map((opcao) => (
									<option key={opcao} value={opcao} />
								))}
							</datalist>
							{erroTipo && (
								<p id={idErroTipo} className="text-body text-danger">
									Informe o tipo de irregularidade.
								</p>
							)}
						</div>
						<div className="flex flex-col gap-1">
							<label htmlFor={idKwh} className="text-small text-text-muted">
								kWh recuperado
							</label>
							<input
								id={idKwh}
								type="text"
								inputMode="decimal"
								value={kwh}
								onChange={(event) => {
									setKwh(event.target.value);
									setErroKwh(false);
								}}
								aria-invalid={erroKwh || undefined}
								aria-describedby={erroKwh ? idErroKwh : undefined}
								className="h-10 w-full rounded-md border border-border bg-transparent px-3 text-body text-text tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-focus-ring aria-invalid:border-danger"
							/>
							{erroKwh && (
								<p id={idErroKwh} className="text-body text-danger">
									Informe o kWh recuperado, maior que zero (ex.: 1.234,5).
								</p>
							)}
						</div>
					</div>
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
