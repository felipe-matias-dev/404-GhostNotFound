import { QueryClient } from "@tanstack/react-query";

// Tabelas Gold são recarregadas em lote: dados podem ficar em cache por alguns minutos.
// Mutations (ex.: ordens de inspeção) devem invalidar as queries afetadas.
const STALE_TIME_MS = 5 * 60 * 1000;

export function getContext() {
	const queryClient = new QueryClient({
		defaultOptions: {
			queries: {
				staleTime: STALE_TIME_MS,
			},
		},
	});

	return {
		queryClient,
	};
}
