import { createFileRoute } from "@tanstack/react-router";
import { AgentePage } from "#/features/agente";

export const Route = createFileRoute("/agente")({
	component: AgentePage,
});
