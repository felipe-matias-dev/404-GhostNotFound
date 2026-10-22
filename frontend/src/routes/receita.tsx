import { createFileRoute } from "@tanstack/react-router";
import { ReceitaPage } from "#/features/receita";

export const Route = createFileRoute("/receita")({ component: ReceitaPage });
