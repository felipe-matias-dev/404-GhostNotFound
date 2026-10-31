import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { VisaoGeralPage } from "#/features/visaoGeral";
import { filtrosCompartilhadosShape } from "#/lib/filtros";

const searchSchema = z.object(filtrosCompartilhadosShape);

export const Route = createFileRoute("/")({
	validateSearch: searchSchema,
	component: VisaoGeralPage,
});
