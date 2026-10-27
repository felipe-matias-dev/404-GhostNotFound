import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import {
	INDICADORES,
	VISOES_TENDENCIA,
	VisaoGeralPage,
} from "#/features/visaoGeral";

// Mesmo formato da tela de Receita (AAAA-MM/AAAA-MM): o período segue de uma tela para a outra.
const periodo = z
	.string()
	.regex(/^\d{4}-\d{2}\/\d{4}-\d{2}$/)
	.optional()
	.catch(undefined);

const searchSchema = z.object({
	periodo_base: periodo,
	periodo_atual: periodo,
	indicador: z.enum(INDICADORES).optional().catch(undefined),
	tendencia: z.enum(VISOES_TENDENCIA).optional().catch(undefined),
});

export const Route = createFileRoute("/")({
	validateSearch: searchSchema,
	component: VisaoGeralPage,
});
