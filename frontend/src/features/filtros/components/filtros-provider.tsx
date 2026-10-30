import { useRouter, useRouterState } from "@tanstack/react-router";
import { createContext, useContext, useEffect, useRef } from "react";
import {
	CAMPOS_COMPARTILHADOS,
	lerFiltrosCompartilhados,
	type DestinoPortal,
	type FiltrosCompartilhados,
} from "#/lib/filtros";
import {
	buscaPara,
	registrar,
	telaDaNavegacao,
	type Memoria,
} from "../memoria";

type Contexto = {
	filtros: FiltrosCompartilhados;
	alterar: (patch: Partial<FiltrosCompartilhados>) => void;
	limparRecorte: () => void;
	searchPara: (destino: DestinoPortal, patch?: Record<string, unknown>) => Record<string, unknown>;
};

const Context = createContext<Contexto | null>(null);

export function FiltrosProvider({ children }: { children: React.ReactNode }) {
	const router = useRouter();
	const state = useRouterState();
	const memoria = useRef<Memoria>({});
	// Uma navegação só vale completa: pathname e busca saem da mesma tela, e a memória só grava
	// depois que ela conclui. Durante a transição o estado misto não vaza.
	const tela = telaDaNavegacao(state);
	const naTela = tela.destino;
	const destino = naTela ?? "/";
	const search = tela.search;
	const filtros = lerFiltrosCompartilhados(destino, search);

	useEffect(() => {
		if (state.isLoading || !state.resolvedLocation || !naTela) return;
		memoria.current = registrar(memoria.current, naTela, search);
	}, [state.isLoading, state.resolvedLocation, naTela, search]);

	function searchPara(alvo: DestinoPortal, patch: Record<string, unknown> = {}) {
		return buscaPara(alvo, { destino: naTela, search, filtros }, memoria.current, patch);
	}

	function alterar(patch: Partial<FiltrosCompartilhados>) {
		if (!naTela) return;
		const compartilhado: Record<string, unknown> = {};
		for (const campo of CAMPOS_COMPARTILHADOS) {
			if (campo in patch) compartilhado[campo] = patch[campo];
		}
		void router.navigate({
			to: naTela,
			search: buscaPara(
				naTela,
				{ destino: naTela, search, filtros },
				memoria.current,
				compartilhado,
			) as never,
			resetScroll: false,
		});
	}

	return (
		<Context.Provider
			value={{
				filtros,
				alterar,
				limparRecorte: () =>
					alterar({ municipio: undefined, bairro: undefined, classe: undefined }),
				searchPara,
			}}
		>
			{children}
		</Context.Provider>
	);
}

export function useFiltrosPortal() {
	const context = useContext(Context);
	if (!context) throw new Error("useFiltrosPortal deve ser usado dentro de FiltrosProvider");
	return context;
}
