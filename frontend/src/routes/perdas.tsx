import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { PerdasPage, STATUS_ORDEM } from "#/features/perdas";

const searchSchema = z.object({
	status: z.enum(STATUS_ORDEM).optional().catch(undefined),
});

export const Route = createFileRoute("/perdas")({
	validateSearch: searchSchema,
	component: PerdasPage,
});
