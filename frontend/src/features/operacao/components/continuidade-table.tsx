import { InfoIcon, MagnifyingGlassIcon } from "@phosphor-icons/react";
import { type ReactElement, useId, useMemo, useState } from "react";
import { Button } from "#/components/ui/button";
import {
	DataTable,
	type DataTableColumn,
	type SortState,
} from "#/components/ui/data-table";
import {
	Tooltip,
	TooltipContent,
	TooltipTrigger,
} from "#/components/ui/tooltip";
import { formatHoras, formatIndice, formatNumero } from "#/lib/format";
import { cn } from "#/lib/utils";
import { filtrarSegmentos } from "../conversions";
import { INDICADORES_REDE } from "../indicadores";
import type {
	Criterio,
	LinhaContinuidade,
	LinhaTabela,
	NivelRecorte,
} from "../types";

const IDENTIFICADOR: Record<NivelRecorte, string> = {
	municipio: "Município",
	bairro: "Bairro",
	alimentador: "Alimentador",
};

// A DataTable só destaca o cabeçalho ordenado. Na ordem da API o índice escolhido ganha
// `text-text` por posição de coluna, sem editar o kit (DEC é a 2ª, FEC a 3ª); com a tabela
// reordenada pelo usuário, o destaque é o do kit.
const DESTAQUE: Record<Criterio, string> = {
	dec: "[&_thead_th:nth-child(2)_span]:text-text [&_dl_div:nth-child(1)_dt]:text-text",
	fec: "[&_thead_th:nth-child(3)_span]:text-text [&_dl_div:nth-child(2)_dt]:text-text",
};

// As colunas na mesma ordem da tabela, cada uma com a definição de onde ela vem.
const AJUDA = [
	["DEC", INDICADORES_REDE.dec.hint],
	["FEC", INDICADORES_REDE.fec.hint],
	["Horas interrompidas", INDICADORES_REDE.horas_interrompidas.hint],
	["Interrupções", INDICADORES_REDE.n_interrupcoes.hint],
	["UCs (média)", INDICADORES_REDE.n_uc_medio.hint],
] as const;

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
	const buscaId = useId();
	const [termo, setTermo] = useState("");
	const [ordem, setOrdem] = useState<SortState | null>(null);
	// Outro conjunto de linhas (nível, período, critério, recorte) começa sem busca e na ordem
	// da API: o termo de um nível não diz nada no seguinte.
	const [chave, setChave] = useState(resetKey);
	if (chave !== resetKey) {
		setChave(resetKey);
		setTermo("");
		setOrdem(null);
	}

	// A posição é a da ordem da API, antes da busca e da ordenação local: o ranking não muda
	// quando a tabela é reordenada ou filtrada.
	const linhas = useMemo<LinhaTabela[] | undefined>(
		() =>
			rows &&
			filtrarSegmentos(
				rows.map((linha, indice) => ({ ...linha, posicao: indice + 1 })),
				termo,
			),
		[rows, termo],
	);

	const identificador = IDENTIFICADOR[nivel];
	const colunas: DataTableColumn<LinhaTabela>[] = [
		{
			id: "segmento",
			header: identificador,
			width: "minmax(0, 1.4fr)",
			value: (linha) => linha.segmento,
			cell: (linha) => (
				<span className="flex min-w-0 items-baseline gap-2">
					<span className="w-7 shrink-0 text-right text-small tabular-nums text-text-muted">
						{linha.posicao}º
					</span>
					<span className="truncate">{linha.segmento}</span>
				</span>
			),
		},
		{
			id: "dec",
			header: "DEC",
			width: "minmax(72px, 0.7fr)",
			align: "end",
			numeric: true,
			value: (linha) => linha.dec,
			cell: (linha) => formatHoras(linha.dec),
		},
		{
			id: "fec",
			header: "FEC",
			width: "minmax(72px, 0.6fr)",
			align: "end",
			numeric: true,
			value: (linha) => linha.fec,
			cell: (linha) => formatIndice(linha.fec),
		},
		{
			id: "horas",
			header: "Horas interrompidas",
			width: "minmax(112px, 0.9fr)",
			align: "end",
			numeric: true,
			value: (linha) => linha.horas_interrompidas,
			cell: (linha) => formatHoras(linha.horas_interrompidas),
		},
		{
			id: "interrupcoes",
			header: "Interrupções",
			width: "minmax(96px, 0.7fr)",
			align: "end",
			numeric: true,
			value: (linha) => linha.n_interrupcoes,
			cell: (linha) => formatNumero(linha.n_interrupcoes),
		},
		{
			id: "ucs",
			header: "UCs (média)",
			width: "minmax(88px, 0.7fr)",
			align: "end",
			numeric: true,
			value: (linha) => linha.n_uc_medio,
			cell: (linha) => formatNumero(linha.n_uc_medio),
		},
	];

	// Linhas de outro recorte ainda não abrem; a falha de uma atualização mantém as atuais.
	const clicavel = !loading && rows !== undefined;
	// O erro nativo substitui a tabela; com linhas na tela, o aviso vem por fora.
	const erroComDados = Boolean(error) && rows !== undefined;
	const busca = termo.trim();

	return (
		<div
			className={cn(
				"flex min-w-0 flex-col gap-2",
				ordem === null && DESTAQUE[criterio],
			)}
		>
			<div className="flex flex-wrap items-center justify-between gap-2">
				<div className="flex h-9 w-full max-w-xs items-center gap-2 rounded-md border border-border-strong bg-surface-2 px-3 focus-within:border-focus-ring focus-within:ring-3 focus-within:ring-focus-ring/50">
					<MagnifyingGlassIcon
						aria-hidden
						className="size-4 shrink-0 text-text-muted"
					/>
					<label htmlFor={buscaId} className="sr-only">
						Buscar {identificador.toLowerCase()}
					</label>
					<input
						id={buscaId}
						type="search"
						autoComplete="off"
						spellCheck={false}
						placeholder={`Buscar ${identificador.toLowerCase()}`}
						value={termo}
						onChange={(event) => setTermo(event.target.value)}
						className="h-full min-w-0 flex-1 bg-transparent text-body text-text outline-none placeholder:text-text-muted"
					/>
				</div>
				<div className="flex items-center gap-2">
					{refreshing && (
						<output className="text-small text-text-muted">Atualizando…</output>
					)}
					<Tooltip>
						<TooltipTrigger
							delay={0}
							render={
								<button
									type="button"
									aria-label="Sobre as colunas da tabela"
									className="grid size-7 shrink-0 place-items-center rounded-sm text-text-muted outline-none transition-colors hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50"
								/>
							}
						>
							<InfoIcon aria-hidden className="size-4" />
						</TooltipTrigger>
						<TooltipContent className="max-w-sm">
							<dl className="flex flex-col gap-1.5">
								{AJUDA.map(([nome, definicao]) => (
									<div key={nome}>
										<dt className="font-medium">{nome}</dt>
										<dd>{definicao}</dd>
									</div>
								))}
							</dl>
						</TooltipContent>
					</Tooltip>
				</div>
			</div>
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
				label={`Continuidade por ${identificador.toLowerCase()}`}
				columns={colunas}
				rows={linhas}
				resetKey={`${resetKey}|${busca}`}
				getRowId={(linha) => linha.segmento}
				getRowLabel={(linha) => rotulo(nivel, linha.segmento)}
				loading={loading || refreshing}
				error={rows === undefined ? error : null}
				onRetry={onRetry}
				emptyMessage={
					busca
						? `Nenhum ${identificador.toLowerCase()} com “${busca}” nesta lista.`
						: "Sem dados de continuidade para este período e recorte."
				}
				sort={ordem}
				onSortChange={setOrdem}
				pageSize={10}
				onRowClick={clicavel ? onOpen : undefined}
			/>
		</div>
	);
}
