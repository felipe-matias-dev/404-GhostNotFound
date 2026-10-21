import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// O tailwind-merge não lê o @theme de styles.css: sem estes nomes, ele confunde
// `text-body` (tamanho) com `text-text` (cor) e `shadow-overlay` com cor de sombra, e
// descarta uma das classes. Mantenha em sincronia com os tokens de styles.css.
const twMerge = extendTailwindMerge({
	extend: {
		theme: {
			text: ["display", "title", "metric", "heading", "body", "small", "code"],
			font: ["sans", "display", "mono"],
			shadow: ["edge", "overlay", "modal"],
		},
	},
});

/** Junta classes condicionais e resolve conflitos do Tailwind (a última vence). */
export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}
