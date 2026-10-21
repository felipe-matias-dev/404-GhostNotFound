import { useSyncExternalStore } from "react";

// Tema da interface: escuro é o padrão (sem atributo); claro é `data-tema="claro"` no <html>,
// que é o seletor que styles.css usa. A escolha fica no localStorage.
export type Tema = "escuro" | "claro";

const CHAVE = "tema";

/** Roda no <head> antes da pintura (ver routes/__root.tsx) para o tema salvo não piscar. */
export const scriptTemaInicial = `try{if(localStorage.getItem("${CHAVE}")==="claro")document.documentElement.dataset.tema="claro"}catch(e){}`;

// Identidades estáveis para o useSyncExternalStore; o atributo do <html> é a fonte da verdade,
// então vários controles de tema ficam sincronizados.
function lerTema(): Tema {
	return document.documentElement.dataset.tema === "claro" ? "claro" : "escuro";
}

function assinarTema(aoMudar: () => void) {
	const observer = new MutationObserver(aoMudar);
	observer.observe(document.documentElement, {
		attributes: true,
		attributeFilter: ["data-tema"],
	});
	return () => observer.disconnect();
}

export function useTema() {
	// No prerender não há document: o servidor assume o padrão (escuro).
	const tema = useSyncExternalStore(
		assinarTema,
		lerTema,
		() => "escuro" as const,
	);

	function definirTema(novo: Tema) {
		const raiz = document.documentElement;
		if (novo === "claro") raiz.dataset.tema = "claro";
		else delete raiz.dataset.tema;
		try {
			localStorage.setItem(CHAVE, novo);
		} catch {
			// Armazenamento bloqueado (modo privado): o tema vale só para esta sessão.
		}
	}

	return { tema, definirTema };
}
