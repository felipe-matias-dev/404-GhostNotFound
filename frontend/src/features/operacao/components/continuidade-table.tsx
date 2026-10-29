import type { ReactElement } from "react";
import { Button } from "#/components/ui/button";
import { DataTable, type DataTableColumn } from "#/components/ui/data-table";
import { formatHoras, formatIndice, formatNumero } from "#/lib/format";
import { cn } from "#/lib/utils";
import type { Criterio, LinhaContinuidade, NivelRecorte } from "../types";

const IDENTIFICADOR: Record<NivelRecorte, string> = {
	municipio: "Município",
	bairro: "Bairro",
	alimentador: "Alimentador",
};

// A DataTable só destaca o cabeçalho ordenado, e aqui a ordem é a da API: o índice escolhido
// ganha `text-text` por posição de coluna, sem editar o kit (DEC é a 2ª, FEC a 3ª).
const DESTAQUE: Record<Criterio, string> = {
	dec: "[&_thead_th:nth-child(2)_span]:text-text [&_dl_div:nth-child(1)_dt]:text-text",
	fec: "[&_thead_th:nth-child(3)_span]:text-text [&_dl_div:nth-child(2)_dt]:text-text",
};

/** O que a linha abre: histórico do alimentador, os bairros de um município ou os de um bairro. */
const rotulo = (nivel: NivelRecorte, segmento: string) => {
	if (nivel === "alimentador") return `histórico do alimentador ${segmento}`;
	if (nivel === "municipio") return `bairros de ${segmento}`;
	return `alimentadores de ${segmento}`;
};

export type ContinuidadeTableProps = {
	rows: LinhaContinuidade[] | undefined;
	nivel: NivelRecorte;
	criterio: Criterio;
	resetKey: string;
	loading: boolean;
	refreshing: boolean;
	error: string | null;
	onRetry: () => void;
	onOpen: (row: LinhaContinuidade) => void;
};

export function ContinuidadeTable({
	rows,
	nivel,
	criterio,
	resetKey,
	loading,
	refreshing,
	error,
	onRetry,
	onOpen,
}: ContinuidadeTableProps): ReactElement {
	const colunas: DataTableColumn<LinhaContinuidade>[] = [
		{
			id: "segmento",
			header: IDENTIFICADOR[nivel],
			width: "minmax(0, 1.6fr)",
			sortable: false,
			value: (linha) => linha.segmento,
		},
		{
			id: "dec",
			header: "DEC",
			width: "minmax(72px, 0.7fr)",
			align: "end",
			numeric: true,
			sortable: false,
			value: (linha) => linha.dec,
			cell: (linha) => formatHoras(linha.dec),
		},
		{
			id: "fec",
			header: "FEC",
			width: "minmax(72px, 0.7fr)",
			align: "end",
			numeric: true,
			sortable: false,
			value: (linha) => linha.fec,
			cell: (linha) => formatIndice(linha.fec),
		},
		{
			id: "ucs",
			header: "UCs (média)",
			width: "minmax(72px, 0.7fr)",
			align: "end",
			numeric: true,
			sortable: false,
			value: (linha) => linha.n_uc_medio,
			cell: (linha) => formatNumero(linha.n_uc_medio),
		},
	];

	// Linhas de outro recorte ainda não abrem; a falha de uma atualização mantém as atuais.
	const clicavel = !loading && rows !== undefined;
	// O erro nativo substitui a tabela; com linhas na tela, o aviso vem por fora.
	const erroComDados = Boolean(error) && rows !== undefined;

	return (
		<div className={cn("flex min-w-0 flex-col gap-2", DESTAQUE[criterio])}>
			{refreshing && (
				<output className="text-small text-text-muted">Atualizando…</output>
			)}
			{erroComDados && (
				<div
					role="alert"
					className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-danger/40 bg-danger-subtle p-3"
				>
					<p className="text-body text-danger">
						A atualização falhou. Os dados anteriores continuam exibidos.
					</p>
					<Button variant="outline" size="sm" onClick={onRetry}>
						Tentar de novo
					</Button>
				</div>
			)}
			<DataTable
				label={`Continuidade por ${IDENTIFICADOR[nivel].toLowerCase()}`}
				columns={colunas}
				rows={rows}
				resetKey={resetKey}
				getRowId={(linha) => linha.segmento}
				getRowLabel={(linha) => rotulo(nivel, linha.segmento)}
				loading={loading || refreshing}
				error={rows === undefined ? error : null}
				onRetry={onRetry}
				emptyMessage="Sem dados de continuidade para este período e recorte."
				sort={null}
				pageSize={10}
				onRowClick={clicavel ? onOpen : undefined}
			/>
		</div>
	);
}
