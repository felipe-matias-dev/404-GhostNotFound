import { createFileRoute } from "@tanstack/react-router";
import { UnidadeConsumidoraPage } from "#/features/unidadeConsumidora";

export const Route = createFileRoute("/uc")({
	component: UnidadeConsumidoraPage,
});
