import { useQuery } from "@tanstack/react-query";
import type { Recorte } from "#/lib/filtros";
import { listarOrdens, ordensKeys } from "../api";
import type { StatusOrdem } from "../types";

function ehObjeto(valor: unknown): valor is Record<string, unknown> {
	return typeof valor === "object" && valor !== null;
}

function juntar(fonte: Record<string, unknown>) {
	const valor = (campo: string) => {
		const dado = fonte[campo];
		return typeof dado === "string" ? dado : "";
	};
	return [valor("municipio"), valor("bairro"), valor("classe")].join("\u0000");
}

/** Identidade estável do recorte: compara consultas e reinicia a tabela ao trocar de geografia. */
export function chaveDoRecorte(recorte: Recorte): string {
	return juntar(recorte);
}

/** Recorte de uma query key já emitida; falha fechada (sem chave conhecida não há reaproveitamento). */
function chaveDoRecorteDaConsulta(
	queryKey: readonly unknown[],
): string | undefined {
	const ultimo = queryKey.at(-1);
	if (!ehObjeto(ultimo)) return undefined;
	return juntar(ehObjeto(ultimo.recorte) ? ultimo.recorte : ultimo);
}

export function useOrdens(status: StatusOrdem | undefined, recorte: Recorte) {
	const chave = chaveDoRecorte(recorte);
	return useQuery({
		queryKey: ordensKeys.lista(status, recorte),
		queryFn: () => listarOrdens(status, recorte),
		// Trocar só o status mantém as linhas do mesmo recorte enquanto chegam as novas; ao mudar
		// município, bairro ou classe, nada do recorte anterior é reaproveitado como se fosse atual.
		placeholderData: (previous, previousQuery) =>
			previous !== undefined &&
			previousQuery !== undefined &&
			chaveDoRecorteDaConsulta(previousQuery.queryKey) === chave
				? previous
				: undefined,
	});
}
