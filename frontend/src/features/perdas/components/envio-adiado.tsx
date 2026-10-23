import { motion, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "#/components/ui/button";
import type { Ordem } from "../types";

/**
 * Quanto tempo o "Enviar a campo" espera antes do PATCH. O backend não deixa uma OI em campo
 * voltar para Gerada (DEC-009), então o desfazer existe só nesta janela, no navegador.
 */
export const JANELA_DESFAZER_MS = 6000;

type Agendado = {
	ordem: Ordem;
	/** Tempo que faltava quando o relógio (re)começou ou parou. */
	restanteMs: number;
	/** Momento em que o relógio voltou a correr; `null` enquanto pausado. */
	desde: number | null;
};

/**
 * Agenda o envio a campo e devolve o que a tela precisa para mostrar o aviso com "Desfazer".
 * O relógio para enquanto o ponteiro ou o foco estão no aviso (tempo ajustável, WCAG 2.2.1).
 * Sair da tela envia na hora o que estava agendado; fechar a aba pede confirmação.
 */
export function useEnvioAdiado(disparar: (ordem: Ordem) => void) {
	const [agendados, setAgendados] = useState<Agendado[]>([]);
	const timers = useRef(new Map<number, number>());
	const atual = useRef({ agendados, disparar });
	atual.current = { agendados, disparar };

	const remover = useCallback((id: number) => {
		window.clearTimeout(timers.current.get(id));
		timers.current.delete(id);
		setAgendados((lista) => lista.filter((a) => a.ordem.id !== id));
	}, []);

	const enviarAgora = useCallback(
		(id: number) => {
			const item = atual.current.agendados.find((a) => a.ordem.id === id);
			remover(id);
			if (item) atual.current.disparar(item.ordem);
		},
		[remover],
	);

	const iniciarRelogio = useCallback(
		(id: number, ms: number) => {
			window.clearTimeout(timers.current.get(id));
			timers.current.set(
				id,
				window.setTimeout(() => enviarAgora(id), ms),
			);
		},
		[enviarAgora],
	);

	const agendar = useCallback(
		(ordem: Ordem) => {
			if (timers.current.has(ordem.id)) return;
			setAgendados((lista) => [
				...lista,
				{ ordem, restanteMs: JANELA_DESFAZER_MS, desde: Date.now() },
			]);
			iniciarRelogio(ordem.id, JANELA_DESFAZER_MS);
		},
		[iniciarRelogio],
	);

	const pausar = useCallback((id: number) => {
		window.clearTimeout(timers.current.get(id));
		setAgendados((lista) =>
			lista.map((a) =>
				a.ordem.id === id && a.desde !== null
					? {
							...a,
							restanteMs: Math.max(0, a.restanteMs - (Date.now() - a.desde)),
							desde: null,
						}
					: a,
			),
		);
	}, []);

	const retomar = useCallback(
		(id: number) => {
			const item = atual.current.agendados.find((a) => a.ordem.id === id);
			if (!item || item.desde !== null) return;
			setAgendados((lista) =>
				lista.map((a) => (a.ordem.id === id ? { ...a, desde: Date.now() } : a)),
			);
			iniciarRelogio(id, item.restanteMs);
		},
		[iniciarRelogio],
	);

	// Fechar a aba com envio agendado: o navegador pergunta antes de perder a ação.
	useEffect(() => {
		if (agendados.length === 0) return;
		const avisar = (event: BeforeUnloadEvent) => event.preventDefault();
		window.addEventListener("beforeunload", avisar);
		return () => window.removeEventListener("beforeunload", avisar);
	}, [agendados.length]);

	// Trocar de tela: o pedido do usuário vale, então o que estava agendado sai na hora.
	useEffect(() => {
		const pendentes = timers.current;
		return () => {
			for (const id of pendentes.keys()) window.clearTimeout(pendentes.get(id));
			for (const { ordem } of atual.current.agendados) {
				atual.current.disparar(ordem);
			}
		};
	}, []);

	return {
		agendados,
		agendar,
		/** Cancela o envio agendado: nada vai para o backend. */
		desfazer: remover,
		enviarAgora,
		pausar,
		retomar,
	};
}

export function AvisoEnvioAdiado({
	agendado,
	onDesfazer,
	onEnviarAgora,
	onPausar,
	onRetomar,
}: {
	agendado: Agendado;
	onDesfazer: () => void;
	onEnviarAgora: () => void;
	onPausar: () => void;
	onRetomar: () => void;
}) {
	const reduced = useReducedMotion() ?? false;
	const { ordem, restanteMs, desde } = agendado;
	const fracao = restanteMs / JANELA_DESFAZER_MS;

	return (
		<section
			aria-label={`Envio da OI ${ordem.id} a campo`}
			onPointerEnter={onPausar}
			onPointerLeave={(event) => {
				if (!event.currentTarget.contains(document.activeElement)) onRetomar();
			}}
			onFocus={onPausar}
			onBlur={(event) => {
				if (!event.currentTarget.contains(event.relatedTarget)) onRetomar();
			}}
			className="relative flex flex-col gap-2 overflow-hidden rounded-lg border border-border-strong bg-surface-2 p-3 shadow-overlay"
		>
			<p className="text-body text-text">
				OI #{ordem.id} vai a campo em instantes.
				{desde === null && (
					<span className="text-text-muted">
						{" "}
						Pausado enquanto você decide.
					</span>
				)}
			</p>
			<div className="flex justify-end gap-2">
				<Button
					size="sm"
					variant="ghost"
					aria-label={`Enviar a OI ${ordem.id} a campo agora`}
					onClick={onEnviarAgora}
				>
					Enviar agora
				</Button>
				<Button
					size="sm"
					variant="outline"
					aria-label={`Desfazer o envio da OI ${ordem.id}`}
					onClick={onDesfazer}
				>
					Desfazer
				</Button>
			</div>
			{/* Barra do tempo que resta; parada quando pausado, ausente com movimento reduzido. */}
			{!reduced && (
				<motion.div
					aria-hidden
					key={desde ?? "pausado"}
					className="absolute inset-x-0 bottom-0 h-0.5 origin-left bg-info"
					initial={{ scaleX: fracao }}
					animate={{ scaleX: desde === null ? fracao : 0 }}
					transition={
						desde === null
							? { duration: 0 }
							: { duration: restanteMs / 1000, ease: "linear" }
					}
				/>
			)}
		</section>
	);
}
