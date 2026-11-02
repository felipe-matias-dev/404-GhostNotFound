export {
	RegionMap,
	type RegionMapProps,
	type RegionMapShape,
} from "./region-map";
export { RMR_CONTEXTO, RMR_MUNICIPIOS, RMR_VIEWBOX } from "./rmr.gen";

export { useBairrosRmr } from "./use-bairros-rmr";
/**
 * Chave para casar o município ou bairro da Gold com o da malha do IBGE: sem acento, caixa
 * ou espaço sobrando ("Jaboatão dos Guararapes" = "JABOATAO DOS GUARARAPES").
 */
export function chaveNome(nome: string): string {
	return nome
		.normalize("NFD")
		.replace(/\p{Diacritic}/gu, "")
		.toLowerCase()
		.replace(/\s+/g, " ")
		.trim();
}
