import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { UnidadeConsumidoraPage } from "#/features/unidadeConsumidora";

export const Route = createFileRoute("/uc")({
	validateSearch: z.object({
		cod_uc: z
			.union([z.string(), z.number()])
			.transform(String)
			.pipe(z.string().trim().min(1))
			.optional()
			.catch(undefined),
	}),
	component: UnidadeConsumidoraPage,
});
