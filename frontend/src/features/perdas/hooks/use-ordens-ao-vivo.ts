import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { filaKey, ordensKeys, URL_AVISOS_ORDENS } from "../api";

/**
 * Mantém a tela de Perdas em dia com as ordens de inspeção sem recarregar: o backend avisa por SSE
 * a cada mudança confirmada no banco, e a tela refaz as consultas (o GET segue sendo a fonte da verdade).
 * A fila entra junto porque mostra qual UC já tem ordem ativa.
 */
export function useOrdensAoVivo() {
	const queryClient = useQueryClient();

	useEffect(() => {
		const origem = new EventSource(URL_AVISOS_ORDENS, {
			withCredentials: true,
		});
		const atualizar = () => {
			void queryClient.invalidateQueries({ queryKey: ordensKeys.all });
			void queryClient.invalidateQueries({ queryKey: filaKey });
		};
		// O aviso não é durável: o que mudou enquanto a conexão estava fora só chega por esta
		// consulta, e o EventSource reabre sozinho depois de uma queda.
		origem.addEventListener("open", atualizar);
		origem.addEventListener("ordens", atualizar);
		return () => origem.close();
	}, [queryClient]);
}
