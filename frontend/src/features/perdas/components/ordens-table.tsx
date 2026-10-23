import { Badge } from "#/components/ui/badge";
import { DataTable, type DataTableColumn } from "#/components/ui/data-table";
import { formatDataHora } from "#/lib/format";
import { RESULTADO_ORDEM_ROTULO, STATUS_ORDEM_VISUAL } from "../conversions";
import { useOrdens } from "../hooks/use-ordens";
import { type Ordem, STATUS_ORDEM, type StatusOrdem } from "../types";

const COLUNAS: DataTableColumn<Ordem>[] = [
	{
		id: "id",
		header: "OI",
		width: "88px",
		numeric: true,
		value: (o) => o.id,
		cell: (o) => `#${o.id}`,
	},
	{ id: "cod_uc", header: "UC", width: "96px", value: (o) => o.cod_uc },
	{
		id: "status",
		header: "Status",
		width: "136px",
		// Ordena pela posição na máquina de estados, e não pelo texto.
		value: (o) => STATUS_ORDEM.indexOf(o.status),
		cell: (o) => {
			const { rotulo, ponto } = STATUS_ORDEM_VISUAL[o.status];
			return (
				<Badge>
					<span
						data-icon="inline-start"
						aria-hidden
						className={`size-1.5 rounded-full ${ponto}`}
					/>
					{rotulo}
				</Badge>
			);
		},
	},
	{
		id: "resultado",
		header: "Resultado",
		value: (o) => (o.resultado ? RESULTADO_ORDEM_ROTULO[o.resultado] : null),
	},
	{
		id: "criada_em",
		header: "Criada em",
		width: "152px",
		numeric: true,
		value: (o) => o.criada_em,
		cell: (o) => formatDataHora(o.criada_em),
	},
	{
		id: "atualizada_em",
		header: "Atualizada em",
		width: "152px",
		numeric: true,
		value: (o) => o.atualizada_em,
		cell: (o) => formatDataHora(o.atualizada_em),
	},
];

export function OrdensTable({ status }: { status: StatusOrdem | undefined }) {
	const { data, isPending, isFetching, isError, refetch } = useOrdens(status);

	return (
		<DataTable
			label="Ordens de inspeção"
			columns={COLUNAS}
			rows={data}
			getRowId={(o) => String(o.id)}
			getRowLabel={(o) => `OI ${o.id} da UC ${o.cod_uc}`}
			loading={isPending || isFetching}
			error={
				isError ? "Não foi possível carregar as ordens de inspeção." : null
			}
			onRetry={() => refetch()}
			emptyMessage={
				status
					? `Nenhuma ordem com status ${STATUS_ORDEM_VISUAL[status].rotulo.toLowerCase()}.`
					: "Nenhuma ordem de inspeção gerada ainda."
			}
		/>
	);
}
