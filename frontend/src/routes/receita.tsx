import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { EFEITOS, ReceitaPage } from "#/features/receita";

const periodo = z
	.string()
	.regex(/^\d{4}-\d{2}\/\d{4}-\d{2}$/)
	.optional()
	.catch(undefined);

const searchSchema = z.object({
	municipio: z.string().min(1).optional().catch(undefined),
	bairro: z.string().min(1).optional().catch(undefined),
	periodo_base: periodo,
	periodo_atual: periodo,
	efeito: z.enum(EFEITOS).optional().catch(undefined),
});

export const Route = createFileRoute("/receita")({
	validateSearch: searchSchema,
	component: ReceitaPage,
});
