import { getRouteApi } from "@tanstack/react-router";
import { Pagina } from "#/components/layout/pagina";
import { IndicadoresMes } from "../components/indicadores-mes";
import { ResumoReceita } from "../components/resumo-receita";
import { janelasDaBase, parEscolhido } from "../conversions";
import { useCompetencias } from "../hooks/use-indicadores";
import type { ParPeriodos } from "../types";

const route = getRouteApi("/");

export function VisaoGeralPage() {
	const { periodo_base, periodo_atual } = route.useSearch();
	const navigate = route.useNavigate();

	// O par da URL só vale se os dois meses existem na série; senão, o padrão.
	const competencias = useCompetencias();
	const par = competencias.data
		? parEscolhido(competencias.data, periodo_base, periodo_atual)
		: undefined;
	const janelas = competencias.data
		? janelasDaBase(competencias.data)
		: undefined;

	const escolher = (proximo: ParPeriodos) =>
		navigate({
			search: (atual) => ({
				...atual,
				periodo_base: proximo.periodo_base,
				periodo_atual: proximo.periodo_atual,
			}),
			resetScroll: false,
		});

	// Série carregada sem nenhum par possível (menos de dois meses): não há o que comparar.
	const semDados = Boolean(competencias.data) && !par;
	return (
		<Pagina className="max-w-none">
			<ResumoReceita
				janelas={janelas}
				semJanelas={Boolean(competencias.data) && !janelas}
				erroSerie={competencias.isError}
				onRetrySerie={() => competencias.refetch()}
			/>
			<IndicadoresMes
				competencias={competencias.data ?? []}
				par={par}
				onEscolher={escolher}
				carregando={competencias.isPending}
				erro={
					competencias.isError
						? "Não foi possível carregar os indicadores."
						: null
				}
				semDados={semDados}
				onRetry={() => competencias.refetch()}
			/>
		</Pagina>
	);
}
