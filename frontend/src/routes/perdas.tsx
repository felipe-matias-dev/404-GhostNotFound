import { createFileRoute } from "@tanstack/react-router";
import { PerdasPage } from "#/features/perdas";
import { perdasSearchSchema } from "#/features/perdas/search";

export const Route = createFileRoute("/perdas")({
	validateSearch: perdasSearchSchema,
	component: PerdasPage,
});
