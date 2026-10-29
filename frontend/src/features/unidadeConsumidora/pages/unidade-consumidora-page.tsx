import { getRouteApi } from "@tanstack/react-router";
import { useEffect } from "react";
import { HeaderTrilha } from "#/components/layout/header";
import { Pagina } from "#/components/layout/pagina";
import {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbList,
	BreadcrumbPage,
	BreadcrumbSeparator,
} from "#/components/ui/breadcrumb";
import { Button } from "#/components/ui/button";
import { DataTable, type DataTableColumn } from "#/components/ui/data-table";
import { SkeletonSwap } from "#/components/ui/skeleton-swap";
import { TrendChart } from "#/components/ui/trend-chart";
import { ApiError } from "#/lib/api";
import { CadastroUc } from "../components/cadastro-uc";
import { useConsultaUc } from "../components/consulta-uc-provider";
import { ConsumoUc } from "../components/consumo-uc";
import {
	ChamadosUc,
	FaturasUc,
	InterrupcoesUc,
} from "../components/historico-uc";
import { useVisao360 } from "../hooks/use-visao-360";

const route = getRouteApi("/uc");
const loadingColumns: DataTableColumn<{ id: string }>[] = [
	{ id: "id", header: "Registro", value: (row) => row.id },
	{ id: "data", header: "Data" },
	{ id: "detalhes", header: "Detalhes" },
];

function CarregandoUc() {
	return (
		<div aria-busy="true" className="flex min-w-0 flex-col gap-5">
			<SkeletonSwap
				ready={false}
				reserve={96}
				lines={3}
				label="Identificação da UC"
			>
				<span className="sr-only">Carregando unidade consumidora</span>
			</SkeletonSwap>
			<div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
				<div className="flex min-w-0 flex-col gap-5">
					<SkeletonSwap
						ready={false}
						reserve={240}
						lines={8}
						label="Consumo faturado"
					>
						<span className="sr-only">Carregando diagnóstico</span>
					</SkeletonSwap>
					<TrendChart label="Histórico de consumo" height={240} loading />
					<DataTable
						label="Faturas em aberto"
						columns={loadingColumns}
						rows={undefined}
						getRowId={(row) => row.id}
						pageSize={5}
						loading
					/>
				</div>
				<SkeletonSwap
					ready={false}
					reserve={600}
					lines={20}
					label="Cadastro, medidor e geração distribuída"
				>
					<span className="sr-only">Carregando cadastro</span>
				</SkeletonSwap>
			</div>
			<DataTable
				label="Interrupções"
				columns={loadingColumns}
				rows={undefined}
				getRowId={(row) => row.id}
				pageSize={5}
				loading
			/>
			<DataTable
				label="Chamados"
				columns={loadingColumns}
				rows={undefined}
				getRowId={(row) => row.id}
				pageSize={5}
				loading
			/>
		</div>
	);
}

export function UnidadeConsumidoraPage() {
	const { cod_uc: codUc } = route.useSearch();
	const { abrir, registrar } = useConsultaUc();
	const query = useVisao360(codUc);
	const data = query.data;
	const naoEncontrada =
		query.error instanceof ApiError && query.error.status === 404;

	useEffect(() => {
		if (data) registrar(data.cadastro.cod_uc);
	}, [data, registrar]);

	return (
		<Pagina className="max-w-none">
			{codUc && (
				<HeaderTrilha>
					<Breadcrumb aria-label="Unidade selecionada" className="min-w-0">
						<BreadcrumbList>
							<BreadcrumbSeparator />
							<BreadcrumbItem className="min-w-0">
								<BreadcrumbPage className="truncate font-mono">
									{codUc}
								</BreadcrumbPage>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</HeaderTrilha>
			)}
			{!codUc ? (
				<section
					aria-labelledby="uc-orientacao"
					className="flex max-w-lg flex-col items-start gap-3 rounded-md border border-border bg-surface-1 p-5"
				>
					<h2 id="uc-orientacao" className="text-heading">
						Busque uma unidade consumidora
					</h2>
					<p className="mt-2 text-body text-text-muted">
						Busque pelo número da conta ou retome uma UC recente.
					</p>
					<Button onClick={abrir}>Buscar UC</Button>
					<p className="text-small text-text-muted">
						Ctrl / ⌘ + K em qualquer tela.
					</p>
				</section>
			) : (
				<>
					<div className="flex flex-wrap items-center justify-between gap-3">
						<Button variant="outline" onClick={abrir}>
							Trocar UC
						</Button>
						<Button
							variant="ghost"
							disabled={query.isFetching}
							onClick={() => void query.refetch()}
						>
							Atualizar dados
						</Button>
					</div>
					<output className="text-small text-text-muted">
						{query.isFetching
							? data
								? "Atualizando"
								: "Carregando UC"
							: data && !query.isError
								? "Histórico da base consultada"
								: null}
					</output>
					{query.isError && (
						<div
							role="alert"
							className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-danger/40 bg-danger-subtle p-4"
						>
							<div>
								<h2 className="text-heading text-danger">
									{naoEncontrada
										? "UC não encontrada"
										: "Não foi possível carregar esta UC."}
								</h2>
								<p className="mt-1 text-body text-danger">
									{data
										? "A atualização falhou. Os dados anteriores desta UC continuam exibidos."
										: naoEncontrada
											? "Confira o número da UC e tente buscar novamente."
											: "Tente novamente para consultar o histórico."}
								</p>
							</div>
							<Button
								variant="outline"
								disabled={query.isFetching}
								onClick={() => void query.refetch()}
							>
								Tentar de novo
							</Button>
						</div>
					)}
					{data ? (
						<>
							<section
								aria-labelledby="uc-identificacao"
								className="border-border border-b pb-5"
							>
								<h2 id="uc-identificacao" className="font-mono text-heading">
									UC {data.cadastro.cod_uc}
								</h2>
								<p className="mt-1 text-body">
									{data.cadastro.titular_mascarado ?? "Titular não informado"}
								</p>
								<p className="mt-1 text-small text-text-muted">
									{data.cadastro.municipio} · {data.cadastro.bairro} ·{" "}
									{data.cadastro.classe_cadastro}
								</p>
							</section>
							<div className="grid items-start gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
								<div className="flex min-w-0 flex-col gap-5">
									<ConsumoUc data={data} />
									<FaturasUc
										codUc={data.cadastro.cod_uc}
										rows={data.faturas_nao_pagas.itens}
									/>
								</div>
								<CadastroUc cadastro={data.cadastro} medidor={data.medidor} />
							</div>
							<div className="text-small text-text-muted">
								Alimentador do cadastro:{" "}
								<span className="font-mono">
									{data.cadastro.cod_alimentador}
								</span>
								. As ocorrências abaixo são as registradas para esta UC.
							</div>
							<InterrupcoesUc
								codUc={data.cadastro.cod_uc}
								rows={data.interrupcoes}
							/>
							<ChamadosUc
								codUc={data.cadastro.cod_uc}
								rows={data.atendimentos}
							/>
						</>
					) : query.isPending ? (
						<CarregandoUc key={codUc} />
					) : null}
				</>
			)}
		</Pagina>
	);
}
