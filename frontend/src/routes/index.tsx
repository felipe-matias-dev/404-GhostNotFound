import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { VisaoGeralPage } from "#/features/visaoGeral";

// Mesmo formato da tela de Receita (AAAA-MM/AAAA-MM): o período segue de uma tela para a outra.
const periodo = z
	.string()
	.regex(/^\d{4}-\d{2}\/\d{4}-\d{2}$/)
	.optional()
	.catch(undefined);

const searchSchema = z.object({
	periodo_base: periodo,
	periodo_atual: periodo,
});

export const Route = createFileRoute("/")({
	validateSearch: searchSchema,
	component: VisaoGeralPage,
});
