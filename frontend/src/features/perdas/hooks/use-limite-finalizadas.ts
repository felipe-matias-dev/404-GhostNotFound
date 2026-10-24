import { useSyncExternalStore } from "react";
import { LIMITES_FINALIZADAS, limiteFinalizadas } from "../conversions";

function assinar(onChange: () => void) {
	window.addEventListener("resize", onChange);
	return () => window.removeEventListener("resize", onChange);
}

function lerSnapshot() {
	return limiteFinalizadas(window.innerHeight);
}

function lerSnapshotNoServidor() {
	return LIMITES_FINALIZADAS[0].limite;
}

export function useLimiteFinalizadas(): number {
	return useSyncExternalStore(assinar, lerSnapshot, lerSnapshotNoServidor);
}
