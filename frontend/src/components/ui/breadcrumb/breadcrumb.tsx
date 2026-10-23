// Breadcrumb do shadcn/ui (`npx shadcn@latest add breadcrumb`, estilo base-nova sobre Base UI)
// adaptado aos tokens da marca VE-360:
// - `text-body`; níveis anteriores em `text-muted` (hover `text`), o atual em `text` médio;
// - separador CaretRight de 12px em `text-muted`;
// - nome acessível em português; a página atual é `<span aria-current="page">`, sem o
//   `role="link"` desabilitado do original (não é link);
// - sem o Ellipsis: os níveis do portal cabem (seção › município › bairro).
// Link do router: `<BreadcrumbLink render={<Link to="…" />} />`.
import { mergeProps } from "@base-ui/react/merge-props";
import { useRender } from "@base-ui/react/use-render";
import { CaretRightIcon } from "@phosphor-icons/react";
import type * as React from "react";
import { cn } from "#/lib/utils";

function Breadcrumb({
	"aria-label": ariaLabel = "Caminho",
	...props
}: React.ComponentProps<"nav">) {
	return <nav aria-label={ariaLabel} data-slot="breadcrumb" {...props} />;
}

function BreadcrumbList({ className, ...props }: React.ComponentProps<"ol">) {
	return (
		<ol
			data-slot="breadcrumb-list"
			className={cn(
				"flex min-w-0 items-center gap-1.5 text-body text-text-muted",
				className,
			)}
			{...props}
		/>
	);
}

function BreadcrumbItem({ className, ...props }: React.ComponentProps<"li">) {
	return (
		<li
			data-slot="breadcrumb-item"
			className={cn("inline-flex min-w-0 items-center gap-1", className)}
			{...props}
		/>
	);
}

function BreadcrumbLink({
	className,
	render,
	...props
}: Omit<useRender.ComponentProps<"a">, "className"> & { className?: string }) {
	return useRender({
		defaultTagName: "a",
		props: mergeProps<"a">(
			{
				className: cn(
					"truncate rounded-sm outline-none transition-colors hover:text-text focus-visible:text-text",
					className,
				),
			},
			props,
		),
		render,
		state: { slot: "breadcrumb-link" },
	});
}

function BreadcrumbPage({ className, ...props }: React.ComponentProps<"span">) {
	return (
		<span
			data-slot="breadcrumb-page"
			aria-current="page"
			className={cn("truncate font-medium text-text", className)}
			{...props}
		/>
	);
}

function BreadcrumbSeparator({
	children,
	className,
	...props
}: React.ComponentProps<"li">) {
	return (
		<li
			data-slot="breadcrumb-separator"
			role="presentation"
			aria-hidden="true"
			className={cn("flex text-text-muted [&>svg]:size-3", className)}
			{...props}
		>
			{children ?? <CaretRightIcon />}
		</li>
	);
}

export {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbLink,
	BreadcrumbList,
	BreadcrumbPage,
	BreadcrumbSeparator,
};
