import { InfoIcon } from "@phosphor-icons/react";
import type { UseQueryResult } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { type ReactElement, type ReactNode, useId, useState } from "react";
import { DataTable, type DataTableColumn } from "#/components/ui/data-table";
import { KpiCard } from "#/components/ui/kpi-card";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "#/components/ui/popover";
import { useFiltrosPortal } from "#/features/filtros";
import { formatHoras, formatNumero } from "#/lib/format";
import { cn } from "#/lib/utils";
import { TAMANHO_PAGINA_UCS } from "../api";
import { type BarraOcorrencias, barrasDeOcorrencias } from "../conversions";
import { useUcsAtingidas } from "../hooks/use-continuidade";
import { INDICADORES_REDE } from "../indicadores";
import type { Periodo, Recorte, ResumoOcorrencias, UcAtingida } from "../types";

// Os números do painel ficam em faixas de cards, como a faixa de indicadores da Rede e a da
// Visão geral. Na largura do painel, duas colunas: em quatro, um total como "34.375,8 h" não
// cabe na fonte dos cards.
const FAIXA =
	"grid grid-cols-2 gap-px border-border border-t bg-border @2xl:grid-cols-4";
const CELULA = "rounded-none border-0 px-5 py-4 shadow-none";

/** Um bloco do painel: título, uma linha de contexto e a ajuda no (i), como na Visão geral. */
function Cartao({
	titulo,
	descricao,
	ajuda,
	faixa = false,
	children,
}: {
	titulo: string;
	descricao?: string;
	ajuda?: ReactNode;
	/** O corpo é uma faixa de cards encostada nas bordas, sem o respiro interno. */
	faixa?: boolean;
	children: ReactNode;
}): ReactElement {
	const id = useId();
	return (
		<section
			aria-labelledby={id}
			className="@container flex min-w-0 shrink-0 flex-col overflow-hidden rounded-md border border-border bg-surface-1 shadow-edge"
		>
			<header className="flex flex-col gap-0.5 px-5 pt-5 pb-3">
				<div className="flex items-center gap-1.5">
					<h3 id={id} className="text-heading">
						{titulo}
					</h3>
					{ajuda && (
						<Popover>
							<PopoverTrigger
								openOnHover
								delay={200}
								aria-label={`Sobre ${titulo.toLowerCase()}`}
								className="grid size-6 place-items-center rounded-sm text-text-muted outline-none transition-colors hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50"
							>
								<InfoIcon aria-hidden className="size-3.5" />
							</PopoverTrigger>
							<PopoverContent className="max-w-72 p-3 text-body">
								{ajuda}
							</PopoverContent>
						</Popover>
					)}
				</div>
				{descricao && <p className="text-small text-text-muted">{descricao}</p>}
			</header>
			<div className={cn(!faixa && "px-5 pb-5")}>{children}</div>
		</section>
	);
}

/** Quanto o alimentador sofreu no período: interrupções, horas e UCs atingidas e reincidentes. */
export function ResumoAlimentador({
	resumo,
}: {
	resumo: UseQueryResult<ResumoOcorrencias>;
}): ReactElement {
	const dados = resumo.data;
	const vazio = dados?.total.n_interrupcoes === 0;
	const comum = {
		loading: resumo.isPending,
		error: resumo.isError ? "Não foi possível carregar as ocorrências." : null,
		onRetry: () => void resumo.refetch(),
		className: CELULA,
	};
	return (
		<Cartao
			titulo="No período"
			descricao={
				vazio
					? "Nenhuma ocorrência neste período e recorte."
					: "Ocorrências que atingiram as UCs do alimentador."
			}
			ajuda="Cada ocorrência conta uma vez por unidade consumidora atingida, como na Gold: não são eventos da rede."
			faixa
		>
			<div className={FAIXA}>
				<KpiCard
					{...comum}
					label="Interrupções"
					value={dados?.total.n_interrupcoes}
					format={formatNumero}
					hint={INDICADORES_REDE.n_interrupcoes.hint}
				/>
				<KpiCard
					{...comum}
					label="Horas interrompidas"
					value={dados?.total.horas_interrompidas}
					format={formatHoras}
					hint={INDICADORES_REDE.horas_interrompidas.hint}
				/>
				<KpiCard
					{...comum}
					label="UCs atingidas"
					value={dados?.total.ucs_atingidas}
					format={formatNumero}
					hint="Unidades consumidoras com pelo menos uma interrupção no período."
				/>
				<KpiCard
					{...comum}
					label="Reincidentes"
					value={dados?.total.ucs_reincidentes}
					format={formatNumero}
					hint={`UCs com ${formatNumero(dados?.reincidencia_min ?? 3)} ou mais interrupções no período. Limite de produto, não regulatório.`}
				/>
			</div>
		</Cartao>
	);
}

/** Barras de horas por grupo: rótulo e valor na mesma linha, a barra logo abaixo. */
function Barras({
	titulo,
	barras,
}: {
	titulo: string;
	barras: BarraOcorrencias[];
}): ReactElement {
	return (
		<figure className="flex min-w-0 flex-col gap-2.5">
			<figcaption className="text-small text-text-muted">{titulo}</figcaption>
			<ul className="flex flex-col gap-2.5">
				{barras.map((barra) => (
					<li key={barra.nome} className="flex flex-col gap-1">
						<div className="flex items-baseline justify-between gap-3 text-small">
							<span className="truncate text-text">{barra.nome}</span>
							<span className="shrink-0 tabular-nums text-text">
								{formatHoras(barra.horas)}
								<span className="text-text-muted">
									{" · "}
									{formatNumero(barra.interrupcoes)}
								</span>
							</span>
						</div>
						<div aria-hidden className="h-1.5 rounded-full bg-surface-2">
							<div
								className="h-full rounded-full bg-chart-1"
								style={{ width: `${barra.fracao * 100}%` }}
							/>
						</div>
					</li>
				))}
			</ul>
		</figure>
	);
}

/** Por que cai: horas por causa registrada e por tipo de ocorrência, das mais horas para as menos. */
export function CausasAlimentador({
	resumo,
}: {
	resumo: ResumoOcorrencias;
}): ReactElement {
	return (
		<Cartao
			titulo="Por que cai"
			descricao="Horas interrompidas e, ao lado, interrupções de cada grupo."
			ajuda="Causa é o que a equipe registrou na ocorrência; quando não registrou, aparece como Não informada. Tipo é a natureza da ocorrência."
		>
			<div className="grid gap-x-8 gap-y-5 @lg:grid-cols-2">
				<Barras
					titulo="Por causa"
					barras={barrasDeOcorrencias(resumo.por_causa)}
				/>
				<Barras
					titulo="Por tipo"
					barras={barrasDeOcorrencias(resumo.por_tipo)}
				/>
			</div>
		</Cartao>
	);
}

/** Quanto cada falta durou: mediana, P90, máxima e quantas passaram do limite de falta longa. */
export function DuracaoAlimentador({
	resumo,
}: {
	resumo: ResumoOcorrencias;
}): ReactElement {
	const { duracao } = resumo;
	return (
		<Cartao
			titulo="Quanto dura"
			descricao="Duração de cada ocorrência no período."
			ajuda={`Metade das ocorrências dura até a mediana, e 9 em cada 10 até o P90. Falta longa é a de ${formatHoras(resumo.longa_h)} ou mais: limite de produto, não regulatório.`}
			faixa
		>
			<div className={FAIXA}>
				<KpiCard
					label="Mediana"
					value={duracao.mediana_h}
					format={formatHoras}
					className={CELULA}
				/>
				<KpiCard
					label="P90"
					value={duracao.p90_h}
					format={formatHoras}
					className={CELULA}
				/>
				<KpiCard
					label="Máxima"
					value={duracao.maxima_h}
					format={formatHoras}
					className={CELULA}
				/>
				<KpiCard
					label={`Com ${formatHoras(resumo.longa_h)} ou mais`}
					value={duracao.n_longas}
					format={formatNumero}
					className={CELULA}
				/>
			</div>
		</Cartao>
	);
}

const COLUNAS_UCS: DataTableColumn<UcAtingida>[] = [
	{
		id: "cod_uc",
		header: "UC",
		width: "minmax(96px, 0.8fr)",
		cell: (uc) => <span className="font-mono">{uc.cod_uc}</span>,
	},
	{
		id: "local",
		header: "Bairro",
		width: "minmax(0, 1.4fr)",
		cell: (uc) => (
			<span className="truncate">
				{uc.bairro && uc.municipio
					? `${uc.bairro}, ${uc.municipio}`
					: "Fora do cadastro"}
			</span>
		),
	},
	{
		id: "horas",
		header: "Horas",
		width: "minmax(80px, 0.7fr)",
		align: "end",
		numeric: true,
		cell: (uc) => formatHoras(uc.horas_interrompidas),
	},
	{
		id: "interrupcoes",
		header: "Interrupções",
		width: "minmax(88px, 0.7fr)",
		align: "end",
		numeric: true,
		cell: (uc) => formatNumero(uc.n_interrupcoes),
	},
	{
		id: "maior",
		header: "Maior",
		width: "minmax(72px, 0.6fr)",
		align: "end",
		numeric: true,
		cell: (uc) => formatHoras(uc.maior_duracao_h),
	},
];

/**
 * Quem mais sofreu: as UCs do alimentador com mais horas sem energia. Como a tabela da Rede, é
 * uma `DataTable` com título acima, e a linha inteira abre a consulta da UC com o recorte.
 */
export function UcsMaisAtingidas({
	alimentador,
	periodo,
	recorte,
}: {
	alimentador: string;
	periodo: Periodo;
	recorte: Recorte;
}): ReactElement {
	const conjunto = [
		alimentador,
		periodo.inicio,
		periodo.fim,
		recorte.municipio ?? "",
		recorte.bairro ?? "",
		recorte.classe ?? "",
	].join("|");
	// Outro alimentador, período ou recorte começa da primeira página.
	const [pagina, setPagina] = useState(1);
	const [chave, setChave] = useState(conjunto);
	if (chave !== conjunto) {
		setChave(conjunto);
		setPagina(1);
	}
	const ucs = useUcsAtingidas(periodo, recorte, alimentador, pagina);
	const { searchPara } = useFiltrosPortal();
	const navigate = useNavigate();
	const id = useId();

	return (
		<section aria-labelledby={id} className="flex min-w-0 flex-col gap-2">
			<header className="flex flex-col gap-0.5">
				<h3 id={id} className="text-heading">
					UCs mais atingidas
				</h3>
				<p className="text-small text-text-muted">
					Das mais horas sem energia para as menos. Clique na linha para abrir a
					consulta da UC.
				</p>
			</header>
			<DataTable
				label={`UCs mais atingidas do alimentador ${alimentador}`}
				columns={COLUNAS_UCS}
				rows={ucs.data?.ucs}
				getRowId={(uc) => uc.cod_uc}
				getRowLabel={(uc) => `consulta da UC ${uc.cod_uc}`}
				loading={ucs.isPending}
				error={
					ucs.isError && !ucs.data ? "Não foi possível carregar as UCs." : null
				}
				onRetry={() => void ucs.refetch()}
				emptyMessage="Nenhuma UC atingida."
				pageSize={TAMANHO_PAGINA_UCS}
				cardsBelow="xl"
				pagination={{
					page: pagina - 1,
					total: ucs.data?.total ?? 0,
					onPageChange: (page) => setPagina(page + 1),
					disabled: ucs.isFetching,
				}}
				onRowClick={(uc) =>
					void navigate({
						to: "/uc",
						search: searchPara("/uc", { cod_uc: uc.cod_uc }) as never,
					})
				}
			/>
		</section>
	);
}
