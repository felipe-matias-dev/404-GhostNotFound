export {
	RegionMap,
	type RegionMapProps,
	type RegionMapShape,
} from "./region-map";
export { RMR_CONTEXTO, RMR_MUNICIPIOS, RMR_VIEWBOX } from "./rmr.gen";

/** Bairros por código IBGE do município (~140 KB): carregados só quando a tela precisa. */
export const carregarBairrosRmr = () =>
	import("./rmr-bairros.gen").then((m) => m.RMR_BAIRROS);
