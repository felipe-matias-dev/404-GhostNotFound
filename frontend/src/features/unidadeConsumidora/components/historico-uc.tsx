import { Badge } from "#/components/ui/badge";
import { DataTable, type DataTableColumn } from "#/components/ui/data-table";
import {
	formatBRL,
	formatCompetencia,
	formatData,
	formatDataHora,
	formatHoras,
	formatNumero,
} from "#/lib/format";
import type { AtendimentoUc, FaturaNaoPaga, InterrupcaoUc } from "../types";

const faturasColumns: DataTableColumn<FaturaNaoPaga>[] = [
	{
		id: "competencia",
		header: "Competência",
		value: (row) => row.competencia,
		cell: (row) => formatCompetencia(row.competencia),
	},
	{
		id: "vencimento",
		header: "Vencimento",
		value: (row) => row.data_vencimento,
		cell: (row) => formatData(row.data_vencimento),
	},
	{
		id: "valor",
		header: "Valor da fatura",
		numeric: true,
		value: (row) => row.receita_faturada,
		cell: (row) => formatBRL(row.receita_faturada),
	},
	{
		id: "situacao",
		header: "Situação",
		value: (row) => row.status_pagamento,
		cell: (row) => (
			<Badge>
				<span
					aria-hidden
					className={`size-1.5 rounded-full ${row.status_pagamento === "em_atraso" ? "bg-warning" : "bg-info"}`}
				/>
				{row.status_pagamento === "em_atraso" ? "Em atraso" : "Em aberto"}
			</Badge>
		),
	},
	{
		id: "atraso",
		header: "Dias em atraso",
		numeric: true,
		value: (row) => row.dias_em_atraso,
		cell: (row) =>
			row.dias_em_atraso == null
				? "Não se aplica"
				: formatNumero(row.dias_em_atraso),
	},
];
const interrupcoesColumns: DataTableColumn<InterrupcaoUc>[] = [
	{
		id: "ocorrencia",
		header: "Ocorrência",
		value: (row) => row.cod_ocorrencia,
		cell: (row) => (
			<span className="break-all font-mono">{row.cod_ocorrencia}</span>
		),
	},
	{
		id: "abertura",
		header: "Abertura",
		value: (row) => row.data_abertura,
		cell: (row) => formatDataHora(row.data_abertura),
	},
	{
		id: "encerramento",
		header: "Encerramento",
		value: (row) => row.data_encerramento,
		cell: (row) => formatDataHora(row.data_encerramento),
	},
	{
		id: "duracao",
		header: "Duração",
		numeric: true,
		value: (row) => row.duracao_horas,
		cell: (row) => formatHoras(row.duracao_horas),
	},
	{
		id: "tipo",
		header: "Tipo / causa",
		value: (row) => row.tipo,
		cell: (row) => (
			<div>
				<p>{row.tipo}</p>
				<p className="text-small text-text-muted">
					{row.causa ?? "Não informada"}
				</p>
			</div>
		),
	},
];
const chamadosColumns: DataTableColumn<AtendimentoUc>[] = [
	{
		id: "protocolo",
		header: "Protocolo",
		value: (row) => row.protocolo,
		cell: (row) => <span className="break-all font-mono">{row.protocolo}</span>,
	},
	{
		id: "abertura",
		header: "Abertura",
		value: (row) => row.data_abertura,
		cell: (row) => formatDataHora(row.data_abertura),
	},
	{
		id: "assunto",
		header: "Assunto / subassunto",
		value: (row) => row.assunto,
		cell: (row) => (
			<div>
				<p>{row.assunto}</p>
				<p className="text-small text-text-muted">
					{row.subassunto ?? "Não informado"}
				</p>
			</div>
		),
	},
	{ id: "canal", header: "Canal", value: (row) => row.canal },
	{
		id: "fechamento",
		header: "Fechamento",
		value: (row) => row.data_fechamento,
		cell: (row) => formatDataHora(row.data_fechamento),
	},
	{
		id: "satisfacao",
		header: "Satisfação",
		numeric: true,
		value: (row) => row.nota_satisfacao,
		cell: (row) =>
			row.nota_satisfacao == null
				? "Não avaliado"
				: `${formatNumero(row.nota_satisfacao)}/5`,
	},
];

export function FaturasUc({
	codUc,
	rows,
}: {
	codUc: string;
	rows: FaturaNaoPaga[];
}) {
	return (
		<section aria-labelledby="uc-faturas" className="min-w-0">
			<h2 id="uc-faturas" className="mb-3 text-heading">
				Faturas em aberto
			</h2>
			<DataTable
				label="Faturas em aberto"
				columns={faturasColumns}
				rows={rows}
				getRowId={(row) => row.competencia}
				resetKey={codUc}
				pageSize={5}
				emptyMessage="Nenhuma fatura em aberto na base consultada."
			/>
		</section>
	);
}
export function InterrupcoesUc({
	codUc,
	rows,
}: {
	codUc: string;
	rows: InterrupcaoUc[];
}) {
	return (
		<section
			aria-labelledby="uc-interrupcoes"
			className="min-w-0 border-border border-t pt-5"
		>
			<h2 id="uc-interrupcoes" className="text-heading">
				Interrupções que afetaram esta UC
			</h2>
			<p className="mt-1 mb-3 text-small text-text-muted">
				Histórico da base. Não indica falta de energia em tempo real.
			</p>
			<DataTable
				label="Interrupções que afetaram esta UC"
				columns={interrupcoesColumns}
				rows={rows}
				getRowId={(row) => row.cod_ocorrencia}
				resetKey={codUc}
				pageSize={5}
				emptyMessage="Nenhuma interrupção registrada para esta UC."
			/>
		</section>
	);
}
export function ChamadosUc({
	codUc,
	rows,
}: {
	codUc: string;
	rows: AtendimentoUc[];
}) {
	return (
		<section
			aria-labelledby="uc-chamados"
			className="min-w-0 border-border border-t pt-5"
		>
			<h2 id="uc-chamados" className="mb-3 text-heading">
				Chamados
			</h2>
			<DataTable
				label="Chamados"
				columns={chamadosColumns}
				rows={rows}
				getRowId={(row) => row.protocolo}
				resetKey={codUc}
				pageSize={5}
				emptyMessage="Nenhum chamado registrado para esta UC."
			/>
		</section>
	);
}
