import { createFileRoute } from "@tanstack/react-router";
import { PerdasPage, perdasSearchSchema } from "#/features/perdas";

export const Route = createFileRoute("/perdas")({
	validateSearch: perdasSearchSchema,
	component: PerdasPage,
});
