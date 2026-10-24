import { useSyncExternalStore } from "react";

/** `true` enquanto a media query casa (ex.: `"(min-width: 48rem)"`); no prerender, `false`. */
export function useMediaQuery(query: string) {
	return useSyncExternalStore(
		(aoMudar) => {
			const mql = window.matchMedia(query);
			mql.addEventListener("change", aoMudar);
			return () => mql.removeEventListener("change", aoMudar);
		},
		() => window.matchMedia(query).matches,
		() => false,
	);
}
