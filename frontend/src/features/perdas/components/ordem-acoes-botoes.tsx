import {
	CheckCircleIcon,
	ClockCounterClockwiseIcon,
	type Icon,
	PaperPlaneTiltIcon,
	XCircleIcon,
} from "@phosphor-icons/react";
import { Button } from "#/components/ui/button";
import { cn } from "#/lib/utils";
import { ACAO_ORDEM_ROTULO, ACOES_POR_STATUS } from "../conversions";
import type { AcaoOrdem, Ordem } from "../types";

const ICONE: Record<AcaoOrdem, Icon> = {
	enviar: PaperPlaneTiltIcon,
	concluir: CheckCircleIcon,
	cancelar: XCircleIcon,
};

// Cor da ação = cor do status a que ela leva (Fundamentos/Estados): enviar vai para "Em campo"
// (info), concluir para "Concluída" (success); cancelar é o vermelho, sem fundo, para não
// competir com a ação principal. Texto na cor semântica sobre o próprio subtle (contraste ≥ 4.5).
const TOM: Record<AcaoOrdem, string> = {
	enviar:
		"border-transparent bg-info-subtle text-info hover:border-info hover:bg-info-subtle",
	concluir:
		"border-transparent bg-success-subtle text-success hover:border-success hover:bg-success-subtle",
	cancelar: "text-danger hover:bg-danger-subtle active:bg-danger-subtle",
};

/**
 * Botões das ações do status atual da OI; com `onHistorico`, também o do histórico (o kanban usa;
 * na tabela e nos cards o histórico abre pela própria linha).
 */
export function OrdemAcoesBotoes({
	ordem,
	onAcao,
	onHistorico,
	pendente = false,
	className,
}: {
	ordem: Ordem;
	onAcao: (acao: AcaoOrdem, ordem: Ordem) => void;
	onHistorico?: (ordem: Ordem) => void;
	pendente?: boolean;
	className?: string;
}) {
	return (
		// biome-ignore lint/a11y/useSemanticElements: grupo de botões de ação, não formulário.
		<div
			role="group"
			aria-label={`Ações da OI ${ordem.id}`}
			aria-busy={pendente || undefined}
			className={cn("flex flex-wrap items-center gap-1", className)}
		>
			{ACOES_POR_STATUS[ordem.status].map((acao) => {
				const Icone = ICONE[acao];
				return (
					<Button
						key={acao}
						size="xs"
						variant={acao === "cancelar" ? "ghost" : "outline"}
						className={TOM[acao]}
						disabled={pendente}
						aria-label={`${ACAO_ORDEM_ROTULO[acao]} a OI ${ordem.id}`}
						onClick={() => onAcao(acao, ordem)}
					>
						<Icone aria-hidden />
						{ACAO_ORDEM_ROTULO[acao]}
					</Button>
				);
			})}
			{onHistorico && (
				<Button
					size="xs"
					variant="ghost"
					className="text-text-muted hover:text-text"
					aria-label={`Histórico da OI ${ordem.id}`}
					onClick={() => onHistorico(ordem)}
				>
					<ClockCounterClockwiseIcon aria-hidden />
					Histórico
				</Button>
			)}
		</div>
	);
}
