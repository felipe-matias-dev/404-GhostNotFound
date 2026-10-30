import { useMutation, useQueryClient } from "@tanstack/react-query";
import { atualizarOrdem, filaKey, ordensKeys } from "../api";
import type { AtualizarOrdem } from "../types";

export function useAtualizarOrdem() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: ({ id, mudanca }: { id: number; mudanca: AtualizarOrdem }) =>
			atualizarOrdem(id, mudanca),
		// Também no erro: um 409 quer dizer que a OI mudou em outro lugar, e a tela precisa do status atual.
		onSettled: () =>
			Promise.all([
				queryClient.invalidateQueries({ queryKey: ordensKeys.all }),
				queryClient.invalidateQueries({ queryKey: filaKey }),
			]),
	});
}
