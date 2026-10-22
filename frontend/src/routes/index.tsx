import { createFileRoute } from "@tanstack/react-router";
import { Logo } from "#/components/layout/logo";
import { ThemeToggle } from "#/components/ui/theme-toggle";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
	return (
		<header className="flex items-center justify-between p-6">
			<Logo />
			<ThemeToggle />
		</header>
	);
}
