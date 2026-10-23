// Trilha do recorte no Header (ex.: Receita › Recife › Boa Viagem ▾). O AppShell guarda o
// elemento do Header num contexto; a página renderiza `<HeaderTrilha>` onde quiser e o
// conteúdo aparece no topo, logo depois do título. Some quando a página desmonta.
import { createContext, type ReactNode, use } from "react";
import { createPortal } from "react-dom";

export const HeaderTrilhaContext = createContext<HTMLElement | null>(null);

export function HeaderTrilha({ children }: { children: ReactNode }) {
	const slot = use(HeaderTrilhaContext);
	return slot ? createPortal(children, slot) : null;
}
