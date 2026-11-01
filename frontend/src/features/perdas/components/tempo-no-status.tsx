import { ClockIcon } from "@phosphor-icons/react";
import { Badge } from "#/components/ui/badge";
import { formatTempoDecorrido } from "#/lib/format";
import { useRelogio } from "#/lib/use-relogio";
import { segundosNoStatus } from "../conversions";
import type { OrdemDaTela } from "../types";

/** Há quanto tempo a OI ativa está no status atual, contando ao vivo, e o selo de atraso. */
export function TempoNoStatus({ ordem }: { ordem: OrdemDaTela }) {
	const agora = useRelogio();
	const tempo = formatTempoDecorrido(segundosNoStatus(ordem, agora));

	return (
		<span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
			<span className="inline-flex items-center gap-1.5 tabular-nums">
				<ClockIcon aria-hidden className="size-4 shrink-0" />
				<span>
					<span className="sr-only">No status atual </span>há {tempo}
				</span>
			</span>
			{ordem.atrasada && <Badge variant="destructive">Atrasada</Badge>}
		</span>
	);
}
