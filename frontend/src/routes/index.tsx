import { createFileRoute } from "@tanstack/react-router";
import { VisaoGeralPage } from "#/features/visaoGeral";

export const Route = createFileRoute("/")({ component: VisaoGeralPage });
