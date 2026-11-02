import { useSyncExternalStore } from "react";

const INTERVALO_MS = 1000;

const ouvintes = new Set<() => void>();
let agora = Date.now();
let temporizador: ReturnType<typeof setInterval> | undefined;

function assinar(ouvinte: () => void) {
	ouvintes.add(ouvinte);
	if (ouvintes.size === 1) {
		agora = Date.now();
		temporizador = setInterval(() => {
			agora = Date.now();
			for (const avisar of ouvintes) avisar();
		}, INTERVALO_MS);
	}
	return () => {
		ouvintes.delete(ouvinte);
		if (ouvintes.size === 0 && temporizador !== undefined) {
			clearInterval(temporizador);
			temporizador = undefined;
		}
	};
}

const lerAgora = () => agora;

/**
 * Instante atual (ms), renovado a cada segundo. Todos os componentes que o usam dividem um único
 * temporizador, que só existe enquanto algum estiver na tela: 200 cartões não são 200 intervalos.
 * Quem mostra um tempo decorrido recalcula a partir de uma data a cada tique, em vez de somar
 * 1 s: uma aba em segundo plano, onde o navegador atrasa o temporizador, volta com o valor certo.
 */
export function useRelogio(): number {
	return useSyncExternalStore(assinar, lerAgora, lerAgora);
}
