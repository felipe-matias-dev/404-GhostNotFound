import { useSyncExternalStore } from "react";
import { lerVisaoSalva } from "../conversions";
import type { VisaoOrdens } from "../types";

const CHAVE = "perdas:visao-ordens";
const EVENTO = "perdas:visao-ordens:atualizada";

// Fallback para quando o localStorage está bloqueado: a escolha vale só nesta sessão.
let visaoEmMemoria: VisaoOrdens | null = null;

function lerSnapshot(): VisaoOrdens {
	if (typeof window === "undefined") return "kanban";
	try {
		const salvo = window.localStorage.getItem(CHAVE);
		return lerVisaoSalva(salvo ?? visaoEmMemoria);
	} catch {
		return lerVisaoSalva(visaoEmMemoria);
	}
}

function assinarVisao(aoMudar: () => void) {
	const aoMudarStorage = (evento: StorageEvent) => {
		if (evento.key === null || evento.key === CHAVE) aoMudar();
	};
	window.addEventListener("storage", aoMudarStorage);
	window.addEventListener(EVENTO, aoMudar);
	return () => {
		window.removeEventListener("storage", aoMudarStorage);
		window.removeEventListener(EVENTO, aoMudar);
	};
}

/** Visão da lista de OIs, salva no localStorage e sincronizada entre abas. */
export function useVisaoOrdens() {
	const visao = useSyncExternalStore<VisaoOrdens>(
		assinarVisao,
		lerSnapshot,
		() => "kanban",
	);

	function definirVisao(nova: VisaoOrdens) {
		visaoEmMemoria = nova;
		try {
			window.localStorage.setItem(CHAVE, nova);
		} catch {
			// Armazenamento bloqueado (modo privado): o fallback em memória mantém a escolha.
		}
		window.dispatchEvent(new Event(EVENTO));
	}

	return { visao, definirVisao };
}
