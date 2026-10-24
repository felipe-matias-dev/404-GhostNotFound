import { DataTable, type DataTableColumn } from "#/components/ui/data-table";
import { formatBRL, formatPeriodo } from "#/lib/format";
import { cn } from "#/lib/utils";
import { filtroAoAbrir, NIVEL_ROTULO, nivelDoFiltro } from "../conversions";
import { useDecomposicao } from "../hooks/use-decomposicao";
import type { DecomposicaoLinha, Recorte } from "../types";

function valor(
	id: keyof DecomposicaoLinha & string,
	header: string,
	pick: (l: DecomposicaoLinha) => number,
	destaque = false,
): DataTableColumn<DecomposicaoLinha> {
	return {
		id,
		header,
		width: "minmax(0, 1fr)",
		align: "end",
		numeric: true,
		value: pick,
		cell: (l) => (
			<span
				className={cn(
					destaque && pick(l) < 0 && "text-danger",
					destaque && pick(l) > 0 && "text-success",
				)}
			>
				{formatBRL(pick(l))}
			</span>
		),
	};
}

// TODO(#23): quando a #23 entrar (API 0.4.0), rodar `npm run gen:api` e acrescentar as
// colunas `efeito_tarifa` ("Efeito tarifa") e `efeito_bandeira` ("Efeito bandeira") depois
// de `efeito_mix`, no mesmo formato das outras.
const COLUNAS_VALORES: DataTableColumn<DecomposicaoLinha>[] = [
	valor("receita_base", "Receita base", (l) => l.receita_base),
	valor("receita_atual", "Receita atual", (l) => l.receita_atual),
	valor("variacao_receita", "Variação", (l) => l.variacao_receita, true),
	valor("efeito_preco", "Efeito preço", (l) => l.efeito_preco),
	valor("efeito_volume", "Efeito volume", (l) => l.efeito_volume),
	valor("efeito_mix", "Efeito mix", (l) => l.efeito_mix),
];

export function DecomposicaoTable({
	filtro,
	onAbrir,
	onDestaque,
}: {
	filtro: Recorte;
	onAbrir: (proximo: Recorte) => void;
	/** Linha sob o ponteiro (`null` ao sair), para o mapa contornar a região. */
	onDestaque?: (linha: DecomposicaoLinha | null) => void;
}) {
	const { data, isPending, isPlaceholderData, isError, refetch } =
		useDecomposicao(filtro);
	// Enquanto o próximo nível carrega, as linhas na tela ainda são do anterior.
	const nivel = data?.[0]?.nivel ?? nivelDoFiltro(filtro);
	// Linhas do nível anterior não abrem: o filtro já é o novo e o recorte sairia trocado.
	const navegavel = nivel !== "classe" && !isPlaceholderData;

	const colunas: DataTableColumn<DecomposicaoLinha>[] = [
		{
			id: "segmento",
			header: NIVEL_ROTULO[nivel],
			width: "minmax(120px, 1.4fr)",
			value: (l) => l.segmento,
		},
		...COLUNAS_VALORES,
	];

	const primeira = data?.[0];

	return (
		<div className="flex flex-col gap-2">
			{primeira && (
				<p className="text-small text-text-muted">
					{formatPeriodo(primeira.periodo_base)} comparado a{" "}
					{formatPeriodo(primeira.periodo_atual)}
				</p>
			)}
			<DataTable
				label={`Ponte de receita por ${NIVEL_ROTULO[nivel].toLowerCase()}`}
				columns={colunas}
				rows={data}
				resetKey={JSON.stringify(filtro)}
				getRowId={(l) => `${l.periodo_base}|${l.periodo_atual}|${l.segmento}`}
				loading={isPending || isPlaceholderData}
				error={isError ? "Não foi possível carregar a ponte de receita." : null}
				onRetry={() => refetch()}
				emptyMessage="Sem decomposição de receita para este recorte."
				cardsBelow="4xl"
				onRowClick={
					navegavel
						? (linha) => {
								const proximo = filtroAoAbrir(filtro, linha);
								if (proximo) onAbrir(proximo);
							}
						: undefined
				}
				onRowHover={navegavel ? onDestaque : undefined}
			/>
		</div>
	);
}
