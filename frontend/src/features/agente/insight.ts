/**
 * Se o insight da tela ficou indisponível: a busca falhou, ou já veio uma resposta sem texto.
 * Antes de qualquer pedido (`data` ainda não existe), não é indisponível: o botão "Gerar" aparece.
 */
export function indisponivelDoInsight(insight: {
	isError: boolean;
	data?: { texto?: string | null };
}): boolean {
	return insight.isError || (insight.data !== undefined && !insight.data.texto);
}
