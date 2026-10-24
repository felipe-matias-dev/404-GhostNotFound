import { useMutation, useQueryClient } from "@tanstack/react-query";
import { criarOrdens, ordensKeys } from "../api";

export function useCriarOrdens() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (codUcs: string[]) => criarOrdens(codUcs),
		onSuccess: () =>
			queryClient.invalidateQueries({ queryKey: ordensKeys.all }),
	});
}
