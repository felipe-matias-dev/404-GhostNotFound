import { useEffect, useState } from "react";
import { buscarAuditoriaIa } from "../api";
import { camposDaAuditoria } from "../conversions";
import type { AuditoriaIa } from "../types";

// Só é montado para o perfil TI: o backend recusa a rota para os outros perfis (403).
export function AgenteAuditoria({ auditId }: { auditId: number }) {
	const [aberta, setAberta] = useState(false);
	const [registro, setRegistro] = useState<AuditoriaIa | null>(null);
	const [erro, setErro] = useState(false);

	useEffect(() => {
		if (!aberta || registro) return;
		setErro(false);
		const controller = new AbortController();
		buscarAuditoriaIa(auditId, controller.signal)
			.then(setRegistro)
			.catch(() => {
				if (!controller.signal.aborted) setErro(true);
			});
		return () => controller.abort();
	}, [aberta, auditId, registro]);

	return (
		<div className="space-y-1.5">
			<button
				type="button"
				onClick={() => setAberta(!aberta)}
				aria-expanded={aberta}
				className="cursor-pointer text-small text-accent underline-offset-2 hover:underline"
			>
				{aberta ? "Ocultar auditoria" : "Ver auditoria"}
			</button>
			{aberta && erro && (
				<p className="text-small text-danger">
					Não foi possível carregar a auditoria.
				</p>
			)}
			{aberta && registro && (
				<dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-md border border-border bg-surface-2/50 p-2.5 text-small">
					{camposDaAuditoria(registro).map((campo) => (
						<div key={campo.rotulo} className="contents">
							<dt className="text-text-muted">{campo.rotulo}</dt>
							<dd className="min-w-0 break-words font-mono text-text">
								{campo.valor}
							</dd>
						</div>
					))}
				</dl>
			)}
		</div>
	);
}
