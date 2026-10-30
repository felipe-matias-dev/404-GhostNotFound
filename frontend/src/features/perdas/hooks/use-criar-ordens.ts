import { useMutation, useQueryClient } from "@tanstack/react-query";
import { criarOrdens, filaKey, ordensKeys } from "../api";

export function useCriarOrdens() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (codUcs: string[]) => criarOrdens(codUcs),
		onSettled: () =>
			Promise.all([
				queryClient.invalidateQueries({ queryKey: ordensKeys.all }),
				queryClient.invalidateQueries({ queryKey: filaKey }),
			]),
	});
}
