import { useRouter, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Button } from "#/components/ui/button";
import { formatPeriodoCurto } from "#/lib/format";
import {
	aplicarPeriodoPadrao,
	gravarFiltrosCompartilhados,
} from "#/lib/filtros";
import { useCompetencias, useLocalidades, usePeriodosDecomposicao } from "../api";
import { CLASSE_ROTULO, parPadrao, parPadraoMensal } from "../conversions";
import { telaDaNavegacao } from "../memoria";
import { ClassePicker } from "./classe-picker";
import { useFiltrosPortal } from "./filtros-provider";
import { NivelMenu } from "./nivel-menu";
import { PeriodoPicker } from "./periodo-picker";

const CAMPOS_REDE = [
	"municipio",
	"bairro",
	"classe",
	"periodo_base",
	"inicio",
	"fim",
] as const;
const CAMPOS_PAR = [
	"municipio",
	"bairro",
	"classe",
	"periodo_base",
	"periodo_atual",
] as const;

const ordenar = (nomes: string[]) =>
	[...new Set(nomes)].sort((a, b) => a.localeCompare(b, "pt-BR"));

export function FiltrosPortal() {
	const router = useRouter();
	const state = useRouterState();
	const { pathname, destino } = telaDaNavegacao(state);
	const { filtros, alterar, limparRecorte, searchPara } = useFiltrosPortal();
	const periodos = usePeriodosDecomposicao();
	const competencias = useCompetencias();
	const localidades = useLocalidades();
	const [aviso, setAviso] = useState(false);

	const bruto = state.location.search as Record<string, unknown>;
	// O padrão só vale enquanto a URL não traz período: par gravado primeiro, série mensal depois.
	const padrao = periodos.data?.length
		? parPadrao(periodos.data)
		: !periodos.isPending && !competencias.isPending
			? parPadraoMensal(competencias.data ?? [])
			: undefined;
	const resolvidos = aplicarPeriodoPadrao(filtros, padrao);
	const compartilhados: Record<string, string | undefined> = destino
		? gravarFiltrosCompartilhados(destino, resolvidos)
		: {};
	const campos: readonly string[] =
		destino === "/rede" ? CAMPOS_REDE : CAMPOS_PAR;
	// Cada contrato de URL tem um período; o outro formato é lixo de link antigo e sai.
	const aliases = destino === "/rede" ? ["periodo_atual"] : ["inicio", "fim"];
	const divergente =
		campos.some((campo) => bruto[campo] !== compartilhados[campo]) ||
		aliases.some((campo) => bruto[campo] !== undefined);
	const invalido = campos.some(
		(campo) => bruto[campo] !== undefined && bruto[campo] !== compartilhados[campo],
	);

	useEffect(() => {
		setAviso(false);
	}, [pathname]);
	useEffect(() => {
		if (
			!destino ||
			state.isLoading ||
			state.matches.length === 0 ||
			!divergente
		) {
			return;
		}
		if (invalido) setAviso(true);
		// `periodo_atual` entra como patch para o padrão valer também na Rede, que o grava
		// como duas pontas e o descarta da URL final.
		void router.navigate({
			to: destino,
			search: searchPara(destino, {
				...compartilhados,
				periodo_atual: resolvidos.periodo_atual,
				periodo_base: resolvidos.periodo_base,
			}) as never,
			replace: true,
			resetScroll: false,
		});
	}, [
		destino,
		state.isLoading,
		state.matches.length,
		divergente,
		invalido,
		router,
		searchPara,
		compartilhados,
		resolvidos.periodo_atual,
		resolvidos.periodo_base,
	]);

	const par =
		filtros.periodo_base && filtros.periodo_atual
			? {
					periodo_base: filtros.periodo_base,
					periodo_atual: filtros.periodo_atual,
				}
			: undefined;

	if (pathname === "/uc") {
		return (
			<div className="border-b border-border px-3 py-4 text-small text-text-muted lg:px-5" role="note">
				<p>
					Contexto da análise:{" "}
					{par
						? `${formatPeriodoCurto(par.periodo_atual)} vs ${formatPeriodoCurto(par.periodo_base)}`
						: "sem período"}{" "}
					· {filtros.municipio ?? "Todos os municípios"}
					{filtros.bairro ? ` · ${filtros.bairro}` : ""} ·{" "}
					{filtros.classe
						? `${filtros.classe} · ${CLASSE_ROTULO[filtros.classe]}`
						: "Todas as classes"}
				</p>
				<p>Consulta individual: o histórico da UC não é limitado pelos filtros da análise.</p>
			</div>
		);
	}
	if (!destino) return null;

	const municipios = ordenar((localidades.data ?? []).map((item) => item.municipio));
	const bairros = ordenar(
		(localidades.data ?? [])
			.filter((item) => item.municipio === filtros.municipio)
			.map((item) => item.bairro),
	);

	return (
		<div
			className="flex flex-wrap items-center gap-x-2 gap-y-2 border-b border-border px-3 py-3 lg:px-5"
			role="group"
			aria-label="Filtros da análise"
		>
			<span className="hidden text-small font-medium text-text-muted sm:inline">Análise</span>
			{pathname !== "/perdas" && (
				<PeriodoPicker
					pares={periodos.data ?? []}
					par={par}
					onEscolher={alterar}
					erro={periodos.isError}
					carregando={periodos.isPending}
					retry={() => {
						void periodos.refetch();
					}}
				/>
			)}
			<NivelMenu
				nivel="Município"
				todos="Todos os municípios"
				valor={filtros.municipio}
				opcoes={municipios}
				carregando={localidades.isPending}
				erro={localidades.isError}
				atual={false}
				onEscolher={(municipio) => alterar({ municipio })}
			/>
			{filtros.municipio && (
				<NivelMenu
					nivel="Bairro"
					todos="Todos os bairros"
					valor={filtros.bairro}
					opcoes={bairros}
					carregando={localidades.isPending}
					erro={localidades.isError}
					atual={false}
					onEscolher={(bairro) => alterar({ bairro })}
				/>
			)}
			<ClassePicker classe={filtros.classe} onEscolher={(classe) => alterar({ classe })} />
			<Button variant="ghost" size="xs" onClick={limparRecorte} aria-label="Limpar recorte">
				<span className="sm:hidden">Limpar</span>
				<span className="hidden sm:inline">Limpar recorte</span>
			</Button>
			{aviso && (
				<span role="status" className="text-small text-text-muted">
					Filtros inválidos foram ajustados.
				</span>
			)}
			{localidades.isError && (
				<span role="status" className="text-small text-text-muted">
					Catálogo de localidades indisponível.{" "}
					<button
						type="button"
						className="underline"
						onClick={() => {
							void localidades.refetch();
						}}
					>
						Tentar novamente
					</button>
				</span>
			)}
		</div>
	);
}
