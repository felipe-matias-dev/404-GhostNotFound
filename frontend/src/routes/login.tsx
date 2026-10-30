import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { LoginPage } from "#/features/auth";

export const Route = createFileRoute("/login")({
	validateSearch: z.object({
		redirect: z.string().optional().catch(undefined),
	}),
	head: () => ({ meta: [{ title: "Entrar | VE-360" }] }),
	component: LoginPage,
});
