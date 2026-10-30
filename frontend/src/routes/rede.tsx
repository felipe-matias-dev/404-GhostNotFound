import { createFileRoute } from "@tanstack/react-router";
import { RedePage, redeSearchSchema } from "#/features/operacao";

export const Route = createFileRoute("/rede")({
	validateSearch: redeSearchSchema,
	component: RedePage,
});
