import { z } from "zod";

const MES = /^\d{4}-(0[1-9]|1[0-2])$/;

const mes = z.string().regex(MES).optional().catch(undefined);
const texto = z.string().trim().min(1).optional().catch(undefined);
const criterio = z.enum(["dec", "fec"]).optional().catch(undefined);

/** Os campos como a tela os lê: todos opcionais, sem combinações obrigatórias. */
type RedeSearchNormalizada = {
	inicio?: string;
	fim?: string;
	criterio?: "dec" | "fec";
	serie?: "dec" | "fec";
	visao?: "alimentadores" | "localidades";
	municipio?: string;
	bairro?: string;
	alimentador?: string;
};

export const redeSearchSchema = z
	.object({
		inicio: mes,
		fim: mes,
		criterio,
		serie: criterio,
		visao: z.enum(["alimentadores", "localidades"]).optional().catch(undefined),
		municipio: texto,
		bairro: texto,
		alimentador: texto,
	})
	.transform((search): RedeSearchNormalizada => {
		// Período só vale com as duas pontas válidas e em ordem; senão a tela resolve o padrão.
		const inicio = search.inicio;
		const fim = search.fim;
		const periodoValido =
			inicio !== undefined && fim !== undefined && inicio <= fim;
		const global = search.visao === "alimentadores";
		const municipio = global ? undefined : search.municipio;
		return {
			inicio: periodoValido ? inicio : undefined,
			fim: periodoValido ? fim : undefined,
			criterio: search.criterio,
			// A série só existe com um alimentador aberto: sozinha, não diz nada.
			serie: search.alimentador ? search.serie : undefined,
			visao: search.visao ?? (municipio ? "localidades" : undefined),
			municipio,
			// Um bairro sem município não tem onde ser procurado.
			bairro: municipio ? search.bairro : undefined,
			alimentador: search.alimentador,
		};
	});

export type RedeSearch = z.infer<typeof redeSearchSchema>;
