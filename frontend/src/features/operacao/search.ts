import { z } from "zod";
import { type Classe, filtrosCompartilhadosShape } from "#/lib/filtros";
import type { VisaoRede } from "./types";

const mes = z.string().optional().catch(undefined);
const texto = z.string().trim().min(1).optional().catch(undefined);
const criterio = z.enum(["dec", "fec"]).optional().catch(undefined);

/** Os campos como a tela os lê: todos opcionais, sem combinações obrigatórias. */
type RedeSearchNormalizada = {
	inicio?: string;
	fim?: string;
	criterio?: "dec" | "fec";
	visao?: VisaoRede;
	municipio?: string;
	bairro?: string;
	alimentador?: string;
	classe?: Classe;
	periodo_base?: string;
};

export const redeSearchSchema = z
	.object({
		inicio: mes,
		fim: mes,
		criterio,
		visao: z
			.enum(["alimentadores", "bairros", "localidades"])
			.optional()
			.catch(undefined),
		municipio: texto,
		bairro: texto,
		classe: filtrosCompartilhadosShape.classe,
		periodo_base: filtrosCompartilhadosShape.periodo_base,
		alimentador: texto,
	})
	.transform((search): RedeSearchNormalizada => {
		const municipio = search.municipio;
		return {
			inicio: search.inicio,
			fim: search.fim,
			criterio: search.criterio,
			visao: search.visao,
			municipio,
			// Um bairro sem município não tem onde ser procurado.
			bairro: municipio ? search.bairro : undefined,
			classe: search.classe,
			periodo_base: search.periodo_base,
			alimentador: search.alimentador,
		};
	});

export type RedeSearch = z.infer<typeof redeSearchSchema>;
