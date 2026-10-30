import { WaterfallChart } from "#/components/ui/waterfall-chart";
import { formatBRL, formatPct, formatPeriodoCurto } from "#/lib/format";
import {
	causaDoPasso,
	type Efeito,
	passosDaPonte,
} from "../conversions";
import { useDecomposicao } from "../hooks/use-decomposicao";
import { CLASSE_ROTULO } from "#/features/filtros/conversions";
import type { ParPeriodos, Recorte } from "#/lib/filtros";

export function PonteWaterfall({
	par,
	recorte,
	efeito,
	onEfeito,
}: {
	par: ParPeriodos | undefined;
	recorte: Recorte;
	/** Causa que ordena a tabela e o ranking; clicar na mesma etapa volta para a variação. */
	efeito: Efeito;
	onEfeito: (efeito: Efeito) => void;
}) {
	const { data, isPending, isPlaceholderData, isError, refetch } =
		useDecomposicao(par, recorte);
	const passos = data ? passosDaPonte(data) : undefined;
	const nome = recorte.bairro ?? recorte.municipio;
	const daClasse = recorte.classe
		? ` da classe ${recorte.classe} · ${CLASSE_ROTULO[recorte.classe]}`
		: "";

	// Períodos das linhas, e não da URL: no drill-down as linhas ainda podem ser do par anterior.
	const linha = data?.[0];
	const base = passos?.[0]?.value ?? 0;
	const variacao = (passos?.at(-1)?.value ?? 0) - base;
	// A pergunta da tela é "onde está a queda?": o resumo cita o que puxou para baixo, mesmo
	// quando o total subiu.
	const quedas = passos
		?.filter((p) => p.kind === "delta" && p.value < 0)
		.sort((a, b) => a.value - b.value);

	const resumo = linha && quedas && (
		<>
			A receita{daClasse}{" "}
			<span className="font-medium text-text">
				{variacao === 0
					? "ficou estável"
					: `${variacao < 0 ? "caiu" : "subiu"} ${formatBRL(Math.abs(variacao))}`}
			</span>
			{base > 0 && ` (${formatPct(variacao / base, { sinal: true })})`} de{" "}
			{formatPeriodoCurto(linha.periodo_base)} para{" "}
			{formatPeriodoCurto(linha.periodo_atual)}.{" "}
			{quedas.length === 0 ? (
				"Nenhum efeito puxou a receita para baixo."
			) : (
				<>
					{quedas.length === 1 ? "Puxou" : "Puxaram"} para baixo:{" "}
					{quedas.map((p, i) => (
						<span key={p.id}>
							{i > 0 && (i === quedas.length - 1 ? " e " : ", ")}
							<span className="text-text">{p.label.toLowerCase()}</span>{" "}
							<span className="text-danger">({formatBRL(p.value)})</span>
						</span>
					))}
					.
				</>
			)}
		</>
	);

	return (
		<WaterfallChart
			label={`Ponte de receita${daClasse} ${nome ? `de ${nome}` : "da empresa"}`}
			steps={passos}
			summary={resumo}
			compareLabel="vs. receita base"
			percentLabel="Sobre a receita base"
			loading={isPending || isPlaceholderData}
			error={isError ? "Não foi possível carregar a ponte de receita." : null}
			onRetry={() => refetch()}
			emptyMessage="Sem decomposição de receita para este recorte."
			selectedId={efeito}
			onSelect={(passo) => {
				const causa = causaDoPasso(passo.id);
				if (causa) onEfeito(causa === efeito ? "variacao" : causa);
			}}
			selectHint="Clique num efeito para ver onde ele pesou."
		/>
	);
}
