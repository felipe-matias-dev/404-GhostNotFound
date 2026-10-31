import { useRouterState } from "@tanstack/react-router";
import { Pagina } from "#/components/layout/pagina";
import {
	useCompetencias,
	useFiltrosPortal,
	usePeriodosDecomposicao,
} from "#/features/filtros";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { EfeitosReceita } from "../components/efeitos-receita";
import { IndicadoresMes } from "../components/indicadores-mes";
import { ResumoReceita } from "../components/resumo-receita";

export function VisaoGeralPage() {
	const { filtros } = useFiltrosPortal();
	const navegando = useRouterState({ select: (state) => state.isLoading });
	const periodos = usePeriodosDecomposicao();
	const competencias = useCompetencias();

	// O período é o da barra comum; resolver padrão é trabalho dela, uma vez na URL.
	const par: ParPeriodos | undefined =
		filtros.periodo_base && filtros.periodo_atual
			? {
					periodo_base: filtros.periodo_base,
					periodo_atual: filtros.periodo_atual,
				}
			: undefined;
	const recorte: Recorte = {
		municipio: filtros.municipio,
		bairro: filtros.bairro,
		classe: filtros.classe,
	};

	// Sem par, pode ser o catálogo ainda chegando ou não haver dois meses para comparar.
	const resolvendo =
		!par && (navegando || periodos.isPending || competencias.isPending);
	const semPeriodo = !par && !resolvendo;

	return (
		<Pagina className="max-w-none gap-4">
			<ResumoReceita par={par} recorte={recorte} semPeriodo={semPeriodo} />
			<EfeitosReceita
				par={par}
				recorte={recorte}
				carregando={resolvendo}
				semPeriodo={semPeriodo}
			/>
			<IndicadoresMes
				par={par}
				recorte={recorte}
				carregando={resolvendo}
				semPeriodo={semPeriodo}
			/>
		</Pagina>
	);
}
