import { useState } from "react";
import {
	DataTable,
	type DataTableColumn,
	type SortState,
} from "#/components/ui/data-table";
import { formatBRL, formatPct } from "#/lib/format";
import { cn } from "#/lib/utils";
import {
	type CampoValor,
	EFEITO_CAMPO,
	type Efeito,
	filtroAoAbrir,
	NIVEL_ROTULO,
	nivelDoFiltro,
	sobreABase,
} from "../conversions";
import { useDecomposicao } from "../hooks/use-decomposicao";
import type { DecomposicaoLinha, ParPeriodos, Recorte } from "../types";

function tomDoSinal(n: number) {
	return n < 0 ? "text-danger" : n > 0 ? "text-success" : undefined;
}

function valor(
	campo: CampoValor,
	header: string,
	comSinal: boolean,
): DataTableColumn<DecomposicaoLinha> {
	return {
		id: campo,
		header,
		width: "minmax(0, 1fr)",
		align: "end",
		numeric: true,
		value: (l) => l[campo],
		cell: (l) => (
			<span className={cn(comSinal && tomDoSinal(l[campo]))}>
				{formatBRL(l[campo])}
			</span>
		),
	};
}

// Variação em % da receita base: sem ela, o maior município sempre domina a ordem em R$.
const VARIACAO_PCT: DataTableColumn<DecomposicaoLinha> = {
	id: "variacao_pct",
	header: "Var. %",
	width: "minmax(0, 0.8fr)",
	align: "end",
	numeric: true,
	value: (l) => sobreABase(l, "variacao"),
	cell: (l) => {
		const pct = sobreABase(l, "variacao");
		return pct === null ? (
			<span className="text-text-muted">—</span>
		) : (
			<span className={tomDoSinal(pct)}>
				{pct > 0 ? "+" : ""}
				{formatPct(pct)}
			</span>
		);
	},
};

// Efeitos na ordem da ponte. O efeito preço fica de fora: é tarifa + bandeira.
const EFEITOS_DA_PONTE: [CampoValor, string][] = [
	["efeito_tarifa", "Tarifa"],
	["efeito_bandeira", "Bandeira"],
	["efeito_volume", "Volume"],
	["efeito_mix", "Mix"],
];

/** Escolher uma causa na ponte ordena pela coluna dela, da maior queda para a maior alta. */
const ordemDo = (efeito: Efeito): SortState | null =>
	efeito === "variacao"
		? null
		: { columnId: EFEITO_CAMPO[efeito], direction: "asc" };

export function DecomposicaoTable({
	par,
	filtro,
	efeito,
	onAbrir,
	onDestaque,
}: {
	par: ParPeriodos | undefined;
	filtro: Recorte;
	/** Causa escolhida na ponte: ordena a tabela e ganha cor de alta e queda. */
	efeito: Efeito;
	onAbrir: (proximo: Recorte) => void;
	/** Linha sob o ponteiro (`null` ao sair), para o mapa contornar a região. */
	onDestaque?: (linha: DecomposicaoLinha | null) => void;
}) {
	const { data, isPending, isPlaceholderData, isError, refetch } =
		useDecomposicao(par, filtro);
	// Enquanto o próximo nível carrega, as linhas na tela ainda são do anterior.
	const nivel = data?.[0]?.nivel ?? nivelDoFiltro(filtro);
	// Linhas do nível anterior não abrem: o filtro já é o novo e o recorte sairia trocado.
	const navegavel = nivel !== "classe" && !isPlaceholderData;

	// A ponte define a ordem; o cabeçalho continua livre até a próxima troca de causa.
	const [ordem, setOrdem] = useState(() => ordemDo(efeito));
	const [efeitoAnterior, setEfeitoAnterior] = useState(efeito);
	if (efeito !== efeitoAnterior) {
		setEfeitoAnterior(efeito);
		setOrdem(ordemDo(efeito));
	}

	const campoDestacado = EFEITO_CAMPO[efeito];
	const colunas: DataTableColumn<DecomposicaoLinha>[] = [
		{
			id: "segmento",
			header: NIVEL_ROTULO[nivel],
			width: "minmax(120px, 1.4fr)",
			value: (l) => l.segmento,
		},
		valor("receita_base", "Receita base", false),
		valor("receita_atual", "Receita atual", false),
		valor("variacao_receita", "Variação", true),
		VARIACAO_PCT,
		...EFEITOS_DA_PONTE.map(([campo, header]) =>
			valor(campo, header, campo === campoDestacado),
		),
	];

	return (
		<DataTable
			label={`Ponte de receita por ${NIVEL_ROTULO[nivel].toLowerCase()}`}
			columns={colunas}
			rows={data}
			resetKey={JSON.stringify({ ...filtro, ...par, efeito })}
			getRowId={(l) => `${l.periodo_base}|${l.periodo_atual}|${l.segmento}`}
			loading={isPending || isPlaceholderData}
			error={isError ? "Não foi possível carregar a ponte de receita." : null}
			onRetry={() => refetch()}
			emptyMessage="Sem decomposição de receita para este recorte."
			cardsBelow="5xl"
			sort={ordem}
			onSortChange={setOrdem}
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
	);
}
