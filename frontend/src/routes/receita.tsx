import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { EFEITOS, ReceitaPage } from "#/features/receita";
import { filtrosCompartilhadosShape } from "#/lib/filtros";

const searchSchema = z.object({
	...filtrosCompartilhadosShape,
	efeito: z.enum(EFEITOS).optional().catch(undefined),
});

export const Route = createFileRoute("/receita")({
	validateSearch: searchSchema,
	component: ReceitaPage,
});
