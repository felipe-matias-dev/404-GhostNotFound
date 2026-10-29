import { SignOutIcon, SpinnerGapIcon } from "@phosphor-icons/react";
import { Button } from "#/components/ui/button";
import { useLogout, useSession } from "../hooks/use-auth";
import { PROFILES } from "../profiles";

export function SessionControls() {
	const { data: user } = useSession();
	const logout = useLogout();
	if (!user) return null;
	return (
		<div className="flex flex-col gap-2 border-t border-border pt-3">
			<div className="flex items-center gap-2 px-1">
				<div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
					<p className="truncate text-body font-medium">{user.nome}</p>
					<p className="text-small text-text-muted">
						{PROFILES[user.perfil].label}
					</p>
				</div>
				<Button
					variant="ghost"
					size="icon-sm"
					aria-label="Sair do portal"
					title="Sair do portal"
					disabled={logout.isPending}
					onClick={() => logout.mutate()}
				>
					{logout.isPending ? (
						<SpinnerGapIcon
							aria-hidden="true"
							className="motion-safe:animate-spin"
						/>
					) : (
						<SignOutIcon aria-hidden="true" />
					)}
				</Button>
			</div>
			{logout.error && (
				<p role="alert" className="text-small text-danger">
					Não foi possível sair. Tente novamente.
				</p>
			)}
		</div>
	);
}
