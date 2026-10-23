import { useEffect, useRef, useState } from "react";
import { Button } from "#/components/ui/button";
import { FloatingLabelTextarea } from "#/components/ui/floating-label";
import { HoldToConfirm } from "#/components/ui/hold-to-confirm";
import { Modal } from "#/components/ui/modal";
import { mensagemErroOrdem } from "../conversions";
import type { AtualizarOrdem, Ordem } from "../types";

export function CancelarOrdemModal({
	ordem,
	open,
	onOpenChange,
	onCancelada,
	onEnviar,
}: {
	ordem: Ordem | null;
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onCancelada: (ordem: Ordem) => void;
	onEnviar: (ordem: Ordem, mudanca: AtualizarOrdem) => Promise<void>;
}) {
	const [observacao, setObservacao] = useState("");
	const [erroApi, setErroApi] = useState<string | null>(null);
	const [enviando, setEnviando] = useState(false);
	const motivo = useRef<HTMLTextAreaElement>(null);

	useEffect(() => {
		if (!open) return;
		setObservacao("");
		setErroApi(null);
		setEnviando(false);
	}, [open]);

	const aoConfirmar = async () => {
		if (!ordem || enviando) return;
		setErroApi(null);
		setEnviando(true);
		try {
			await onEnviar(ordem, {
				status: "CANCELADA",
				observacao: observacao.trim() || undefined,
			});
			onCancelada(ordem);
		} catch (error) {
			setErroApi(
				mensagemErroOrdem(
					error,
					`Não foi possível cancelar a OI #${ordem.id}.`,
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
			closeOnEscape={!enviando}
			closeOnBackdrop={!enviando}
			// Foco no motivo, e não na confirmação: cancelar não tem volta.
			initialFocusRef={motivo}
			title={`Cancelar OI #${ordem?.id}`}
			description={`UC ${ordem?.cod_uc} · cancelar não pode ser desfeito. Para inspecionar a UC de novo, gere outra OI.`}
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
					<HoldToConfirm
						tone="destructive"
						confirmLabel="Cancelando…"
						disabled={enviando}
						onConfirm={() => {
							void aoConfirmar();
						}}
					>
						{enviando ? "Cancelando…" : "Segure para cancelar"}
					</HoldToConfirm>
				</>
			}
		>
			<div className="flex flex-col gap-4">
				<FloatingLabelTextarea
					inputRef={motivo}
					label="Motivo do cancelamento (opcional)"
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
			</div>
		</Modal>
	);
}
