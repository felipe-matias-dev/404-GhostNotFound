import { useQuery } from "@tanstack/react-query";
import {
	getRouteApi,
	Link,
	useLocation,
	useRouterState,
} from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Button } from "#/components/ui/button";
import { DataTable, type DataTableColumn } from "#/components/ui/data-table";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "#/components/ui/sheet";
import { useSession } from "#/features/auth";
import { useFiltrosPortal } from "#/features/filtros";
import type { components } from "#/lib/api-schema.gen";
import { formatKWh } from "#/lib/format";
import { filaKey, listarFila, TAMANHO_PAGINA } from "../api";
import { mensagemErroOrdem } from "../conversions";
import { useCriarOrdens } from "../hooks/use-criar-ordens";
import {
	filtrosDaBusca,
	normalizacaoLocal,
	type PerdasSearch,
	paginaDaBusca,
	patchDaOrdenacao,
	patchDaPagina,
	patchDosFiltros,
	recorteDaBusca,
	sortDaBusca,
} from "../search";
import type { FiltrosFila } from "../types";
import { FiltrosSuspeitas } from "./filtros-suspeitas";

type FilaItem = components["schemas"]["FilaItemSchema"];

const route = getRouteApi("/perdas");

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
		cell: (item) => <UcDaFila codUc={item.cod_uc} />,
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

function UcDaFila({ codUc }: { codUc: string }) {
	const { searchPara } = useFiltrosPortal();
	return (
		<Link
			to="/uc"
			search={searchPara("/uc", { cod_uc: codUc }) as never}
			className="relative z-10 text-accent-text underline underline-offset-2"
		>
			{codUc}
		</Link>
	);
}

export function FilaSuspeitas({ onVerOrdens }: { onVerOrdens: () => void }) {
	const { data: user } = useSession();
	const canEdit = user?.perfil === "perdas";
	const search = route.useSearch();
	const navigate = route.useNavigate();
	// A URL bruta ainda pode trazer campos que o schema descartou (valor fora da faixa, faixa
	// invertida, default explícito): comparar com a forma canônica revela o que reescrever.
	const buscaBruta = useLocation({
		select: (local) => local.search,
	}) as Record<string, unknown>;
	const normalizacao = useMemo(
		() => normalizacaoLocal(buscaBruta, search),
		[buscaBruta, search],
	);
	const navegando = useRouterState({ select: (estado) => estado.isLoading });
	const [avisos, setAvisos] = useState<string[]>([]);

	// O aviso sobrevive à reescrita da URL: ele descreve o que foi ignorado, não o estado atual.
	useEffect(() => {
		if (normalizacao.avisos.length > 0) setAvisos(normalizacao.avisos);
	}, [normalizacao]);

	// Normalizar durante uma navegação desfaria a ação do usuário.
	useEffect(() => {
		if (navegando || !normalizacao.altera) return;
		void navigate({
			search: (prev) => ({ ...prev, ...normalizacao.canonico }),
			replace: true,
			resetScroll: false,
		});
	}, [navegando, normalizacao, navigate]);
	const pagina = paginaDaBusca(search);
	const sort = sortDaBusca(search);
	const filtros = filtrosDaBusca(search);
	const recorte = recorteDaBusca(search);
	const [selecionadas, setSelecionadas] = useState<string[]>([]);
	const [mensagem, setMensagem] = useState("");
	const [geradas, setGeradas] = useState(false);
	const [detalhe, setDetalhe] = useState<FilaItem | null>(null);

	// A chave carrega o recorte em posições fixas: assim o placeholder de uma troca só aparece
	// quando a geografia é a mesma (mudança de sinal local), nunca entre recortes diferentes.
	const { data, isPending, isPlaceholderData, isError, refetch } = useQuery({
		queryKey: [
			...filaKey,
			recorte.municipio,
			recorte.bairro,
			recorte.classe,
			pagina,
			sort,
			filtros,
		],
		queryFn: () => listarFila(pagina, sort, filtros, recorte),
		placeholderData: (anterior, consultaAnterior) => {
			const chave = consultaAnterior?.queryKey;
			const mesmoRecorte =
				chave?.[1] === recorte.municipio &&
				chave?.[2] === recorte.bairro &&
				chave?.[3] === recorte.classe;
			return mesmoRecorte ? anterior : undefined;
		},
	});
	const criar = useCriarOrdens();
	const atualizando = isPending || isPlaceholderData;
	const elegiveis = data?.itens.filter((item) => !item.ordem_ativa) ?? [];
	const selecionadasValidas = selecionadas.filter((cod) =>
		elegiveis.some((item) => item.cod_uc === cod),
	);
	const comFiltro =
		filtros.queda !== null ||
		filtros.medidorEletromecanico ||
		filtros.leiturasEstimadas !== null ||
		Object.keys(recorte).length > 0;

	const assinatura = [
		search.municipio,
		search.bairro,
		search.classe,
		search.queda_min,
		search.queda_max,
		search.medidor_eletromecanico,
		search.leituras_estimadas_min,
		search.leituras_estimadas_max,
		pagina,
		search.ordenar_por,
		search.direcao,
	].join("|");

	// biome-ignore lint/correctness/useExhaustiveDependencies: seleção pertence ao recorte e página atuais.
	useEffect(() => {
		setSelecionadas([]);
		setDetalhe(null);
		setMensagem("");
		setGeradas(false);
	}, [assinatura]);

	function navegar(patch: Partial<PerdasSearch>) {
		setAvisos([]);
		void navigate({
			search: (prev) => ({ ...prev, ...patch }),
			resetScroll: false,
		});
	}

	function aplicarFiltros(next: FiltrosFila) {
		navegar(patchDosFiltros(next));
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
					{isPlaceholderData && <output className="ml-2">Atualizando…</output>}
					{canEdit && (
						<span className="ml-2">Selecione UCs sem ordem ativa.</span>
					)}
				</p>
				<div className="flex flex-wrap items-center gap-2">
					<FiltrosSuspeitas
						value={filtros}
						disabled={criar.isPending}
						recorte={recorte}
						onChange={aplicarFiltros}
					/>
					{canEdit && (
						<Button
							size="sm"
							onClick={gerar}
							disabled={
								selecionadasValidas.length === 0 ||
								criar.isPending ||
								atualizando
							}
						>
							{criar.isPending ? "Gerando…" : "Gerar ordens de inspeção"}
						</Button>
					)}
				</div>
			</div>
			{avisos.length > 0 && (
				<output className="flex flex-col gap-1 text-small text-text-muted">
					{avisos.map((aviso) => (
						<p key={aviso}>{aviso}</p>
					))}
				</output>
			)}
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
					comFiltro
						? "Nenhuma unidade consumidora atende a esses filtros."
						: "Nenhuma unidade na fila de suspeitas."
				}
				sort={sort}
				serverSort
				onSortChange={(next) => {
					if (criar.isPending) return;
					navegar(patchDaOrdenacao(next));
				}}
				pageSize={data?.tamanho ?? TAMANHO_PAGINA}
				pagination={{
					page: pagina - 1,
					total: data?.total ?? 0,
					onPageChange: (page) => navegar(patchDaPagina(page + 1)),
					disabled: criar.isPending || atualizando,
				}}
				selected={canEdit ? new Set(selecionadasValidas) : undefined}
				onSelectedChange={
					canEdit ? (selected) => setSelecionadas([...selected]) : undefined
				}
				isRowSelectable={(item) =>
					!item.ordem_ativa && !criar.isPending && !atualizando
				}
				onRowClick={(item) => {
					if (!atualizando) setDetalhe(item);
				}}
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
