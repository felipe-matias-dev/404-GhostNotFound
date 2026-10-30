import { useMutation, useQueryClient } from "@tanstack/react-query";
import { enviarPlanilhaCampo, filaKey, ordensKeys } from "../api";

export function useEnviarPlanilha() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (arquivo: File) => enviarPlanilhaCampo(arquivo),
		onSettled: () =>
			Promise.all([
				queryClient.invalidateQueries({ queryKey: ordensKeys.all }),
				queryClient.invalidateQueries({ queryKey: filaKey }),
			]),
	});
}
