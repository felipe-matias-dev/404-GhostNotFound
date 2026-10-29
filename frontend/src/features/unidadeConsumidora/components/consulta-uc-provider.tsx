import {
	ArrowElbowDownLeftIcon,
	BuildingsIcon,
	CircleNotchIcon,
	ClockCounterClockwiseIcon,
	MagnifyingGlassIcon,
} from "@phosphor-icons/react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { motion, useReducedMotion } from "motion/react";
import {
	createContext,
	type KeyboardEvent,
	type ReactNode,
	use,
	useCallback,
	useEffect,
	useId,
	useRef,
	useState,
} from "react";
import { Button } from "#/components/ui/button";
import { Modal } from "#/components/ui/modal";
import { ApiError } from "#/lib/api";
import { buscarVisao360, unidadeConsumidoraKeys } from "../api";
import { adicionarRecente, parseRecentes, RECENTES_UC_KEY } from "../recentes";

const ConsultaUcContext = createContext<{
	abrir: () => void;
	registrar: (codigo: string) => void;
} | null>(null);

export function useConsultaUc() {
	const context = use(ConsultaUcContext);
	if (!context) throw new Error("Consulta de UC requer ConsultaUcProvider");
	return context;
}

export function ConsultaUcProvider({ children }: { children: ReactNode }) {
	const [open, setOpen] = useState(false);
	const [recentes, setRecentes] = useState<string[]>([]);
	const [loaded, setLoaded] = useState(false);
	const [localDisponivel, setLocalDisponivel] = useState(true);
	const pedido = useRef<AbortController | null>(null);
	const abrir = useCallback(() => setOpen(true), []);
	const fechar = useCallback(() => {
		pedido.current?.abort();
		setOpen(false);
	}, []);
	const registrar = useCallback((codigo: string) => {
		setRecentes((previous) =>
			previous[0] === codigo ? previous : adicionarRecente(previous, codigo),
		);
	}, []);

	useEffect(() => {
		try {
			const salvos = parseRecentes(localStorage.getItem(RECENTES_UC_KEY));
			setRecentes((previous) =>
				[...new Set([...previous, ...salvos])].slice(0, 5),
			);
		} catch {
			setLocalDisponivel(false);
		}
		setLoaded(true);
	}, []);

	useEffect(() => {
		if (!loaded || !localDisponivel) return;
		try {
			localStorage.setItem(RECENTES_UC_KEY, JSON.stringify(recentes));
		} catch {
			setLocalDisponivel(false);
		}
	}, [recentes, loaded, localDisponivel]);

	useEffect(() => {
		function shortcut(event: globalThis.KeyboardEvent) {
			if (
				event.defaultPrevented ||
				event.repeat ||
				event.altKey ||
				!(event.ctrlKey || event.metaKey) ||
				event.key.toLowerCase() !== "k"
			)
				return;
			if (!open && document.querySelector('[aria-modal="true"]')) return;
			event.preventDefault();
			if (open) fechar();
			else setOpen(true);
		}
		window.addEventListener("keydown", shortcut);
		return () => window.removeEventListener("keydown", shortcut);
	}, [open, fechar]);

	return (
		<ConsultaUcContext value={{ abrir, registrar }}>
			{children}
			<ConsultaUcPalette
				open={open}
				onClose={fechar}
				recentes={recentes}
				limpar={() => setRecentes([])}
				localDisponivel={localDisponivel}
				pedido={pedido}
			/>
		</ConsultaUcContext>
	);
}

function ConsultaUcPalette({
	open,
	onClose,
	recentes,
	limpar,
	localDisponivel,
	pedido,
}: {
	open: boolean;
	onClose: () => void;
	recentes: string[];
	limpar: () => void;
	localDisponivel: boolean;
	pedido: React.RefObject<AbortController | null>;
}) {
	const input = useRef<HTMLInputElement>(null);
	return (
		<Modal
			open={open}
			onClose={onClose}
			title="Consulta de UC"
			initialFocusRef={input}
			maxWidth={560}
			maxHeight="min(85dvh, 560px)"
			className="bg-surface-1"
		>
			{open && (
				<BuscaUc
					inputRef={input}
					onClose={onClose}
					recentes={recentes}
					limpar={limpar}
					localDisponivel={localDisponivel}
					pedido={pedido}
				/>
			)}
		</Modal>
	);
}

function BuscaUc({
	inputRef,
	onClose,
	recentes,
	limpar,
	localDisponivel,
	pedido,
}: {
	inputRef: React.RefObject<HTMLInputElement | null>;
	onClose: () => void;
	recentes: string[];
	limpar: () => void;
	localDisponivel: boolean;
	pedido: React.RefObject<AbortController | null>;
}) {
	const [texto, setTexto] = useState("");
	const [selecionado, setSelecionado] = useState<string | null>(null);
	const [pendente, setPendente] = useState<string | null>(null);
	const [erro, setErro] = useState<{ mensagem: string; codigo?: string } | null>(null);
	const queryClient = useQueryClient();
	const navigate = useNavigate();
	const { registrar } = useConsultaUc();
	const reduced = useReducedMotion();
	const uid = useId();
	const codigo = texto.trim();
	const filtrados = recentes.filter(
		(item) =>
			item.toLowerCase().includes(codigo.toLowerCase()) && item !== codigo,
	);
	const opcoes = codigo ? [codigo, ...filtrados] : recentes;
	const ativo =
		selecionado && opcoes.includes(selecionado) ? selecionado : opcoes[0];
	const index = opcoes.indexOf(ativo);

	useEffect(() => () => pedido.current?.abort(), [pedido]);

	async function consultar(valor: string) {
		if (pendente === valor) return;
		pedido.current?.abort();
		const controller = new AbortController();
		pedido.current = controller;
		setPendente(valor);
		setErro(null);
		try {
			const data = await buscarVisao360(valor, controller.signal);
			if (controller.signal.aborted) return;
			queryClient.setQueryData(
				unidadeConsumidoraKeys.visao360(data.cadastro.cod_uc),
				data,
			);
			await navigate({ to: "/uc", search: { cod_uc: data.cadastro.cod_uc } });
			if (!controller.signal.aborted) {
				registrar(data.cadastro.cod_uc);
				onClose();
			}
		} catch (error) {
			if (controller.signal.aborted) return;
			setErro({
				codigo: valor,
				mensagem:
					error instanceof ApiError && error.status === 404
						? "UC não encontrada. Confira o código informado."
						: "Não foi possível consultar esta UC. Tente de novo.",
			});
		} finally {
			if (!controller.signal.aborted) setPendente(null);
		}
	}

	function teclado(event: KeyboardEvent<HTMLInputElement>) {
		if (event.nativeEvent.isComposing) return;
		if (
			["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key) &&
			opcoes.length
		) {
			event.preventDefault();
			const next =
				event.key === "Home"
					? 0
					: event.key === "End"
						? opcoes.length - 1
						: (index + (event.key === "ArrowDown" ? 1 : -1) + opcoes.length) %
							opcoes.length;
			setSelecionado(opcoes[next]);
		} else if (event.key === "Enter") {
			event.preventDefault();
			if (ativo) void consultar(ativo);
			else setErro({ mensagem: "Informe o número da UC." });
		}
	}

	return (
		<div className="flex min-w-0 flex-col gap-3">
			<div className="flex h-11 items-center gap-2 rounded-md border border-border-strong bg-surface-2 px-3 focus-within:border-focus-ring focus-within:ring-3 focus-within:ring-focus-ring/50">
				<MagnifyingGlassIcon
					aria-hidden
					className="size-4 shrink-0 text-text-muted"
				/>
				<input
					ref={inputRef}
					type="text"
					role="combobox"
					aria-label="Número da UC"
					aria-expanded
					aria-controls={`${uid}-lista`}
					aria-autocomplete="list"
					aria-activedescendant={
						ativo ? `${uid}-${opcoes.indexOf(ativo)}` : undefined
					}
					aria-describedby={`${uid}-dica`}
					aria-invalid={Boolean(erro)}
					autoComplete="off"
					spellCheck={false}
					placeholder="Digite o número da UC"
					value={texto}
					onChange={(event) => {
						pedido.current?.abort();
						setPendente(null);
						setErro(null);
						setSelecionado(null);
						setTexto(event.target.value);
					}}
					onKeyDown={teclado}
					className="h-full min-w-0 flex-1 bg-transparent text-body text-text outline-none placeholder:text-text-muted focus-visible:shadow-none"
				/>
				{pendente && (
					<CircleNotchIcon
						aria-hidden
						className="size-4 shrink-0 animate-spin text-text-muted motion-reduce:animate-none"
					/>
				)}
			</div>
			<p id={`${uid}-dica`} className="text-small text-text-muted">
				Busque pelo código da conta ou escolha uma UC recente.
			</p>
			<div className="flex h-6 items-center justify-between gap-2">
				<p className="text-small text-text-muted">
					{codigo ? "Consultar unidade" : "Consultas recentes"}
				</p>
				{recentes.length > 0 && (
					<Button size="xs" variant="ghost" onClick={limpar}>
						Limpar recentes
					</Button>
				)}
			</div>
			<div className="min-h-56">
				<div
					id={`${uid}-lista`}
					role="listbox"
					aria-label="Unidades consumidoras"
					aria-busy={Boolean(pendente)}
					className="flex flex-col gap-1"
				>
					{opcoes.map((item, i) => {
						const isRecent = !codigo || i > 0;
						const Icone = isRecent ? ClockCounterClockwiseIcon : BuildingsIcon;
						return (
							<motion.div
								key={item}
								layout={reduced ? false : "position"}
								transition={
									reduced
										? { duration: 0 }
										: {
												type: "spring",
												stiffness: 520,
												damping: 34,
												mass: 0.45,
											}
								}
							>
								<button
									id={`${uid}-${i}`}
									type="button"
									role="option"
									aria-selected={item === ativo}
									tabIndex={-1}
									onPointerMove={() => setSelecionado(item)}
									onMouseDown={(event) => event.preventDefault()}
									onClick={() => void consultar(item)}
									className={`flex h-10 w-full cursor-pointer items-center gap-3 rounded-md px-3 text-left text-body outline-none focus-visible:ring-3 focus-visible:ring-focus-ring/50 ${item === ativo ? "bg-hover text-text" : "text-text-muted"}`}
								>
									<Icone
										aria-hidden
										className="size-4 shrink-0 text-text-muted"
									/>
									<span className="min-w-0 flex-1 truncate font-mono">
										UC {item}
									</span>
									<span className="shrink-0 text-small text-text-muted">
										{isRecent ? "Recente" : "Consultar"}
									</span>
									{item === ativo && (
										<ArrowElbowDownLeftIcon
											aria-hidden
											className="size-3 shrink-0 text-text-muted"
										/>
									)}
								</button>
							</motion.div>
						);
					})}
				</div>
				{!opcoes.length && (
					<p className="px-3 py-8 text-body text-text-muted">
						Nenhuma UC consultada neste navegador.
					</p>
				)}
			</div>
			{erro && (
				<div
					role="alert"
					className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-danger/40 bg-danger-subtle p-3"
				>
					<p className="text-body text-danger">{erro.mensagem}</p>
					{erro.codigo && (
						<Button
							variant="outline"
							size="sm"
							disabled={Boolean(pendente)}
							onClick={() => {
								if (erro.codigo) void consultar(erro.codigo);
							}}
						>
							Tentar de novo
						</Button>
					)}
				</div>
			)}
			<output className="text-small text-text-muted">
				{pendente
					? `Consultando UC ${pendente}…`
					: localDisponivel
						? "Recentes salvos apenas neste navegador."
						: "Armazenamento indisponível. Recentes mantidos apenas nesta sessão."}
			</output>
			<div className="flex flex-wrap gap-x-4 gap-y-1 border-border border-t pt-3 text-small text-text-muted">
				<span>↑ ↓ selecionar</span>
				<span>Enter consultar</span>
				<span>Esc fechar</span>
			</div>
		</div>
	);
}
