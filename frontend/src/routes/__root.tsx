import { SpinnerGapIcon } from "@phosphor-icons/react";
import { TanStackDevtools } from "@tanstack/react-devtools";
import type { QueryClient } from "@tanstack/react-query";
import {
	createRootRouteWithContext,
	HeadContent,
	Navigate,
	Outlet,
	Scripts,
	useLocation,
} from "@tanstack/react-router";
import { TanStackRouterDevtoolsPanel } from "@tanstack/react-router-devtools";
import { AppShell } from "#/components/layout/app-shell";
import { NAVEGACAO, organizarNavegacao } from "#/components/layout/app-sidebar";
import { Logo } from "#/components/layout/logo";
import { Button } from "#/components/ui/button";
import { AgenteProvider, AgenteWidget } from "#/features/agente";
import {
	PROFILES,
	SessionControls,
	useSession,
	useSessionExpiry,
} from "#/features/auth";
import {
	FiltrosPortal,
	FiltrosProvider,
	useFiltrosPortal,
} from "#/features/filtros";
import {
	ConsultaUcProvider,
	useConsultaUc,
} from "#/features/unidadeConsumidora";
import { scriptTemaInicial } from "#/lib/tema";
import { NaoEncontrado } from "#/pages/nao-encontrado";
import TanStackQueryDevtools from "../integrations/tanstack-query/devtools";
import appCss from "../styles.css?url";

interface MyRouterContext {
	queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
	head: () => ({
		meta: [
			{
				charSet: "utf-8",
			},
			{
				name: "viewport",
				content: "width=device-width, initial-scale=1",
			},
			{
				title: "V-Energy Grid 360",
			},
			{
				name: "theme-color",
				content: "#080a0f",
			},
		],
		links: [
			{
				rel: "stylesheet",
				href: appCss,
			},
			{ rel: "icon", href: "/favicon.svg", type: "image/svg+xml" },
			{
				rel: "icon",
				href: "/favicon-32.png",
				type: "image/png",
				sizes: "32x32",
			},
			{
				rel: "icon",
				href: "/favicon-16.png",
				type: "image/png",
				sizes: "16x16",
			},
			{ rel: "apple-touch-icon", href: "/apple-touch-icon.png" },
			{ rel: "manifest", href: "/manifest.webmanifest" },
		],
		// Aplica o tema salvo antes da primeira pintura (sem piscar o escuro no claro).
		scripts: [{ children: scriptTemaInicial }],
	}),
	shellComponent: RootDocument,
	component: RootLayout,
	notFoundComponent: NaoEncontrado,
});

function RootLayout() {
	useSessionExpiry();
	const session = useSession();
	const location = useLocation();
	const loginPage = location.pathname === "/login";

	if (session.isPending || session.isError) {
		return (
			<main className="flex min-h-svh flex-col items-center justify-center gap-6 bg-bg px-6 text-center">
				<Logo />
				{session.isError ? (
					<div
						role="alert"
						className="flex max-w-sm flex-col items-center gap-4"
					>
						<p className="text-body text-text-muted">
							Não foi possível verificar sua sessão. Confira a conexão e tente
							novamente.
						</p>
						<Button
							onClick={() => void session.refetch()}
							disabled={session.isFetching}
						>
							{session.isFetching ? "Verificando…" : "Tentar novamente"}
						</Button>
					</div>
				) : (
					<output className="flex items-center gap-2 text-body text-text-muted">
						<SpinnerGapIcon
							aria-hidden="true"
							className="size-4 motion-safe:animate-spin"
						/>
						Verificando sua sessão…
					</output>
				)}
			</main>
		);
	}

	if (!session.data) {
		return loginPage ? (
			<Outlet />
		) : (
			<Navigate
				to="/login"
				search={{ redirect: location.href === "/" ? undefined : location.href }}
				replace
			/>
		);
	}
	if (loginPage)
		return <Navigate to={PROFILES[session.data.perfil].home} replace />;

	return (
		<FiltrosProvider key={session.data.login}>
			<ConsultaUcProvider usuario={session.data.login}>
				<AgenteProvider usuario={session.data.login}>
					<Portal />
				</AgenteProvider>
			</ConsultaUcProvider>
		</FiltrosProvider>
	);
}

function Portal() {
	const { abrir } = useConsultaUc();
	const { searchPara } = useFiltrosPortal();
	const { data: user } = useSession();
	const itens = organizarNavegacao(
		NAVEGACAO,
		user ? PROFILES[user.perfil].primaryRoutes : [],
	);
	return (
		<>
			<AppShell
				onConsultarUc={abrir}
				itens={itens}
				conta={<SessionControls />}
				searchPara={searchPara}
			>
				<FiltrosPortal />
				<Outlet />
			</AppShell>
			<AgenteWidget />
			<TanStackDevtools
				config={{ position: "bottom-left" }}
				plugins={[
					{ name: "Tanstack Router", render: <TanStackRouterDevtoolsPanel /> },
					TanStackQueryDevtools,
				]}
			/>
		</>
	);
}

function RootDocument({ children }: { children: React.ReactNode }) {
	return (
		// O script do tema pode pôr `data-tema` no <html> antes da hidratação.
		<html lang="pt-BR" suppressHydrationWarning>
			<head>
				<HeadContent />
			</head>
			<body>
				{children}
				<Scripts />
			</body>
		</html>
	);
}
