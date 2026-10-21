import { createFileRoute } from "@tanstack/react-router";
import { Logo } from "#/components/layout/logo";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
	return (
		<header className="p-6">
			<Logo />
		</header>
	);
}
