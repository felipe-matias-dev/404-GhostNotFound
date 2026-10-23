import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { ReceitaPage } from "#/features/receita";

const searchSchema = z.object({
	municipio: z.string().min(1).optional().catch(undefined),
	bairro: z.string().min(1).optional().catch(undefined),
});

export const Route = createFileRoute("/receita")({
	validateSearch: searchSchema,
	component: ReceitaPage,
});
