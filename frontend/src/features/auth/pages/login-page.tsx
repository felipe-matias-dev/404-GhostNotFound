import {
	ArrowRightIcon,
	EyeIcon,
	EyeSlashIcon,
	LockKeyIcon,
	PauseIcon,
	PlayIcon,
	SpinnerGapIcon,
	WarningCircleIcon,
} from "@phosphor-icons/react";
import { useState } from "react";
import { Logo } from "#/components/layout/logo";
import { Button } from "#/components/ui/button";
import { FloatingLabelInput } from "#/components/ui/floating-label";
import { EnergyNetwork } from "../components/energy-network";
import { falhaDoLogin } from "../conversions";
import { useLogin } from "../hooks/use-auth";
import "../login.css";

export function LoginPage() {
	const login = useLogin();
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const [showPassword, setShowPassword] = useState(false);
	const [paused, setPaused] = useState(false);
	const [entered, setEntered] = useState(false);
	const falha = login.error ? falhaDoLogin(login.error) : null;
	const invalid = falha?.credenciaisInvalidas ?? false;

	return (
		<main
			className="login-page relative isolate flex min-h-svh flex-col overflow-hidden bg-bg text-text"
			data-entered={entered}
			onFocusCapture={() => setEntered(true)}
			onAnimationEnd={(event) => {
				if (event.animationName === "login-reveal") setEntered(true);
			}}
		>
			<div
				className="pointer-events-none absolute inset-0 -z-10"
				aria-hidden="true"
			>
				<EnergyNetwork paused={paused} />
				<div className="login-network-mask absolute inset-0" />
			</div>

			<div className="login-stage relative mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 py-8">
				<div className="login-brand mb-8 flex flex-col items-center gap-4 text-center">
					<Logo className="text-metric" />
					<p className="max-w-64 text-pretty text-body text-text-muted">
						Toda a sua energia. Uma só visão.
					</p>
				</div>

				<section
					className="login-card rounded-lg border border-border-strong bg-surface-1 p-6 shadow-edge sm:p-8"
					aria-labelledby="login-title"
				>
					<div className="mb-4">
						<h1
							id="login-title"
							className="text-balance font-display text-heading"
						>
							Entre na sua operação
						</h1>
						<p className="mt-2 text-pretty text-body text-text-muted">
							Use suas credenciais para acessar o portal.
						</p>
					</div>

					<form
						onSubmit={(event) => {
							event.preventDefault();
							if (!login.isPending)
								login.mutate({ login: username.trim(), senha: password });
						}}
						className="flex flex-col gap-2"
						aria-busy={login.isPending}
					>
						<FloatingLabelInput
							label="Usuário"
							name="username"
							autoComplete="username"
							value={username}
							onChange={(value) => {
								setUsername(value);
								login.reset();
							}}
							maxLength={50}
							className="[&>div:last-child]:hidden"
							required
							invalid={invalid}
							readOnly={login.isPending}
						/>
						<div className="relative">
							<FloatingLabelInput
								label="Senha"
								name="password"
								type={showPassword ? "text" : "password"}
								autoComplete="current-password"
								value={password}
								onChange={(value) => {
									setPassword(value);
									login.reset();
								}}
								maxLength={200}
								required
								invalid={invalid}
								readOnly={login.isPending}
								className="[&_input]:pr-12 [&>div:last-child]:hidden"
							/>
							<Button
								type="button"
								variant="ghost"
								size="icon-sm"
								className="absolute right-1 bottom-1 text-text-muted"
								aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
								aria-pressed={showPassword}
								onClick={() => setShowPassword(!showPassword)}
							>
								{showPassword ? (
									<EyeSlashIcon aria-hidden="true" />
								) : (
									<EyeIcon aria-hidden="true" />
								)}
							</Button>
						</div>

						{falha && (
							<div
								role="alert"
								className="mt-2 flex items-start gap-2 rounded-md bg-danger-subtle p-3 text-body text-danger"
							>
								<WarningCircleIcon
									aria-hidden="true"
									className="mt-0.5 size-4 shrink-0"
								/>
								<p>{falha.mensagem}</p>
							</div>
						)}

						<Button
							type="submit"
							size="lg"
							className="mt-6 w-full justify-between"
							disabled={login.isPending}
						>
							{login.isPending ? "Entrando…" : "Entrar no portal"}
							{login.isPending ? (
								<SpinnerGapIcon
									aria-hidden="true"
									className="motion-safe:animate-spin"
								/>
							) : (
								<ArrowRightIcon aria-hidden="true" />
							)}
						</Button>
						<output className="sr-only">
							{login.isPending ? "Validando suas credenciais." : ""}
						</output>
					</form>

					<p className="mt-6 border-t border-border pt-4 text-pretty text-small text-text-muted">
						Precisa de acesso? Solicite suas credenciais à equipe de TI.
					</p>
				</section>
				<p className="login-caption mt-6 flex items-center justify-center gap-2 text-small text-text-muted">
					<LockKeyIcon aria-hidden="true" className="size-3.5" />
					Portal corporativo
				</p>
			</div>

			<footer className="flex items-center justify-end gap-4 px-6 py-4 text-small text-text-muted sm:px-10">
				<Button
					type="button"
					variant="ghost"
					size="sm"
					className="login-motion-control text-text-muted"
					onClick={() => setPaused(!paused)}
					aria-pressed={paused}
					aria-label={
						paused ? "Retomar animação de fundo" : "Pausar animação de fundo"
					}
				>
					{paused ? (
						<PlayIcon aria-hidden="true" />
					) : (
						<PauseIcon aria-hidden="true" />
					)}
					<span className="hidden sm:inline">
						{paused ? "Retomar animação" : "Pausar animação"}
					</span>
				</Button>
			</footer>
		</main>
	);
}
