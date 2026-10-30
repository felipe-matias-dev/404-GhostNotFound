import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "#/components/ui/button";
import {
	DataTable,
	type DataTableColumn,
	type SortState,
} from "#/components/ui/data-table";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "#/components/ui/sheet";
import { useSession } from "#/features/auth";
import type { components } from "#/lib/api-schema.gen";
import { formatKWh } from "#/lib/format";
import { filaKey, listarFila, TAMANHO_PAGINA } from "../api";
import { mensagemErroOrdem } from "../conversions";
import { useCriarOrdens } from "../hooks/use-criar-ordens";
import { FILTROS_FILA_INICIAIS, type FiltrosFila } from "../types";
import { FiltrosSuspeitas } from "./filtros-suspeitas";

type FilaItem = components["schemas"]["FilaItemSchema"];

const COLUNAS: DataTableColumn<FilaItem>[] = [
	{
		id: "prioridade",
		header: "Prioridade",
		width: "100px",
		cell: (item) => `${item.score_suspeita}º`,
	},
	{
		id: "uc",
		header: "UC",
		width: "120px",
		cell: (item) => (
			<Link
				to="/uc"
				search={{ cod_uc: item.cod_uc }}
				className="relative z-10 text-accent-text underline underline-offset-2"
			>
				{item.cod_uc}
			</Link>
		),
	},
	{
		id: "queda",
		header: "Queda",
		width: "100px",
		numeric: true,
		sortable: true,
		cell: (item) =>
			item.queda_percentual == null
				? "Não informada"
				: `${item.queda_percentual}%`,
	},
	{
		id: "motivos",
		header: "Motivos da suspeita",
		width: "minmax(16rem, 1fr)",
		cell: (item) => (
			<span className="text-text-muted">
				{item.motivos.join("; ") || "Não informado"}
			</span>
		),
	},
	{
		id: "energia",
		header: "Energia est. (kWh/mês)",
		width: "200px",
		align: "end",
		numeric: true,
		sortable: true,
		cell: (item) =>
			formatKWh(
				item.kwh_recuperavel_est == null
					? null
					: Number(item.kwh_recuperavel_est),
			),
	},
	{
		id: "ordem_ativa",
		header: "Ordem ativa",
		width: "120px",
		sortable: true,
		cell: (item) =>
			item.ordem_ativa ? `#${item.ordem_ativa.id}` : "Sem ordem",
	},
];

export function FilaSuspeitas({ onVerOrdens }: { onVerOrdens: () => void }) {
	const { data: user } = useSession();
	const canEdit = user?.perfil === "perdas";
	const [pagina, setPagina] = useState(1);
	const [sort, setSort] = useState<SortState | null>(null);
	const [filtros, setFiltros] = useState<FiltrosFila>(FILTROS_FILA_INICIAIS);
	const [selecionadas, setSelecionadas] = useState<string[]>([]);
	const [mensagem, setMensagem] = useState("");
	const [geradas, setGeradas] = useState(false);
	const [detalhe, setDetalhe] = useState<FilaItem | null>(null);
	const { data, isPending, isError, refetch } = useQuery({
		queryKey: [...filaKey, pagina, sort, filtros],
		queryFn: () => listarFila(pagina, sort, filtros),
	});
	const criar = useCriarOrdens();
	const elegiveis = data?.itens.filter((item) => !item.ordem_ativa) ?? [];
	const selecionadasValidas = selecionadas.filter((cod) =>
		elegiveis.some((item) => item.cod_uc === cod),
	);

	function mudarPagina(proxima: number) {
		setSelecionadas([]);
		setMensagem("");
		setGeradas(false);
		setPagina(proxima);
	}

	function gerar() {
		setMensagem("");
		setGeradas(false);
		criar.mutate(selecionadasValidas, {
			onSuccess: (ordens) => {
				setSelecionadas([]);
				setGeradas(true);
				setMensagem(
					`${ordens.length} ${ordens.length === 1 ? "OI gerada" : "OIs geradas"}.`,
				);
			},
			onError: (erro) =>
				setMensagem(mensagemErroOrdem(erro, "Não foi possível gerar as OIs.")),
		});
	}

	return (
		<section aria-label="Fila de suspeitas" className="flex flex-col gap-4">
			<div className="flex flex-wrap items-center justify-between gap-3">
				<p className="text-small text-text-muted" aria-live="polite">
					<span className="font-medium text-text">
						{selecionadasValidas.length > 0
							? `${selecionadasValidas.length} ${selecionadasValidas.length === 1 ? "UC selecionada" : "UCs selecionadas"}`
							: data
								? `${data.total} ${data.total === 1 ? "suspeita" : "suspeitas"}`
								: "Carregando fila…"}
					</span>
					{canEdit && (
						<span className="ml-2">Selecione UCs sem ordem ativa.</span>
					)}
				</p>
				<div className="flex flex-wrap items-center gap-2">
					<FiltrosSuspeitas
						value={filtros}
						disabled={criar.isPending}
						onChange={(next) => {
							setFiltros(next);
							mudarPagina(1);
						}}
					/>
					{canEdit && (
						<Button
							size="sm"
							onClick={gerar}
							disabled={selecionadasValidas.length === 0 || criar.isPending}
						>
							{criar.isPending ? "Gerando…" : "Gerar ordens de inspeção"}
						</Button>
					)}
				</div>
			</div>
			{mensagem && (
				<div className="flex flex-wrap items-center gap-2">
					<output aria-live="polite" className="text-small text-text">
						{mensagem}
					</output>
					{geradas && (
						<Button variant="link" size="sm" onClick={onVerOrdens}>
							Ver ordens
						</Button>
					)}
				</div>
			)}
			<DataTable
				label="Fila de suspeitas"
				columns={COLUNAS}
				cardsBelow="5xl"
				rows={data?.itens}
				getRowId={(item) => item.cod_uc}
				getRowLabel={(item) => `UC ${item.cod_uc}`}
				loading={isPending}
				error={isError ? "Não foi possível carregar a fila." : null}
				onRetry={() => refetch()}
				emptyMessage={
					filtros.queda ||
					filtros.medidorEletromecanico ||
					filtros.leiturasEstimadas
						? "Nenhuma unidade consumidora atende a esses filtros."
						: "Nenhuma unidade na fila de suspeitas."
				}
				sort={sort}
				serverSort
				onSortChange={(next) => {
					if (criar.isPending) return;
					setSort(next);
					mudarPagina(1);
				}}
				pageSize={data?.tamanho ?? TAMANHO_PAGINA}
				pagination={{
					page: pagina - 1,
					total: data?.total ?? 0,
					onPageChange: (page) => mudarPagina(page + 1),
					disabled: criar.isPending,
				}}
				selected={canEdit ? new Set(selecionadasValidas) : undefined}
				onSelectedChange={
					canEdit ? (selected) => setSelecionadas([...selected]) : undefined
				}
				isRowSelectable={(item) => !item.ordem_ativa && !criar.isPending}
				onRowClick={setDetalhe}
			/>
			<Sheet
				open={detalhe !== null}
				onOpenChange={(open) => {
					if (!open) setDetalhe(null);
				}}
			>
				<SheetContent side="right">
					<SheetHeader>
						<SheetTitle>Suspeita da UC {detalhe?.cod_uc}</SheetTitle>
						<SheetDescription>
							Motivos identificados na fila de suspeitas.
						</SheetDescription>
					</SheetHeader>
					<p className="whitespace-pre-line px-4 text-body">
						{detalhe?.motivos.length
							? detalhe.motivos.join("\n\n")
							: "Não informado"}
					</p>
				</SheetContent>
			</Sheet>
		</section>
	);
}
