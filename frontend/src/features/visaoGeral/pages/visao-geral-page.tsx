import { getRouteApi } from "@tanstack/react-router";
import { Pagina } from "#/components/layout/pagina";
import { ComparacaoPicker } from "../components/comparacao-picker";
import { IndicadoresCards } from "../components/indicadores-cards";
import { parEscolhido } from "../conversions";
import {
	useComparacaoIndicadores,
	useCompetencias,
} from "../hooks/use-indicadores";
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
	const comparacao = useComparacaoIndicadores(par);

	const escolher = (proximo: ParPeriodos) =>
		navigate({
			search: {
				periodo_base: proximo.periodo_base,
				periodo_atual: proximo.periodo_atual,
			},
			resetScroll: false,
		});

	// Série carregada sem nenhum par possível (menos de dois meses): não há o que comparar.
	const semDados = Boolean(competencias.data) && !par;
	return (
		<Pagina>
			<div className="flex justify-end">
				<ComparacaoPicker
					competencias={competencias.data ?? []}
					par={par}
					onEscolher={escolher}
					semPeriodos={competencias.isError || semDados}
				/>
			</div>
			<IndicadoresCards
				comparacao={comparacao.data}
				par={par}
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
