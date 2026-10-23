import {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useMemo,
	useState,
} from "react";
import { Button } from "#/components/ui/button";
import { mensagemErroOrdem } from "../conversions";
import { useAtualizarOrdem } from "../hooks/use-atualizar-ordem";
import type { AcaoOrdem, AtualizarOrdem, Ordem } from "../types";
import { CancelarOrdemModal } from "./cancelar-ordem-modal";
import { ConcluirOrdemModal } from "./concluir-ordem-modal";
import { AvisoEnvioAdiado, useEnvioAdiado } from "./envio-adiado";
import { HistoricoOrdemSheet } from "./historico-ordem-sheet";

type AcoesOrdemContexto = {
	/**
	 * `enviar` agenda o PATCH (com "Desfazer" durante a janela); `concluir` e `cancelar` abrem
	 * o modal do formulário.
	 */
	abrir: (acao: AcaoOrdem, ordem: Ordem) => void;
	abrirHistorico: (ordem: Ordem) => void;
	/** `true` com envio agendado ou PATCH desta OI em andamento. */
	pendente: (id: number) => boolean;
};

const AcoesOrdemContext = createContext<AcoesOrdemContexto | null>(null);

export function useAcoesOrdem() {
	const contexto = useContext(AcoesOrdemContext);
	if (!contexto) {
		throw new Error(
			"useAcoesOrdem precisa estar dentro de AcoesOrdemProvider.",
		);
	}
	return contexto;
}

type TipoPainel = "concluir" | "cancelar" | "historico";

type PainelAberto = { tipo: TipoPainel; ordem: Ordem; open: boolean };

export function AcoesOrdemProvider({ children }: { children: ReactNode }) {
	const [pendentes, setPendentes] = useState<ReadonlySet<number>>(
		() => new Set(),
	);
	const [mensagem, setMensagem] = useState("");
	const [erroEnvio, setErroEnvio] = useState<string | null>(null);
	const [painel, setPainel] = useState<PainelAberto | null>(null);
	// mutateAsync, e não mutate com callbacks: os callbacks do mutate só disparam para a
	// última chamada, e duas OIs enviadas em seguida deixariam a primeira pendente para sempre.
	const { mutateAsync } = useAtualizarOrdem();

	const enviar = useCallback(
		async (ordem: Ordem, mudanca: AtualizarOrdem) => {
			setPendentes((prev) => new Set(prev).add(ordem.id));
			try {
				await mutateAsync({ id: ordem.id, mudanca });
			} finally {
				setPendentes((prev) => {
					const next = new Set(prev);
					next.delete(ordem.id);
					return next;
				});
			}
		},
		[mutateAsync],
	);

	const enviarACampo = useCallback(
		(ordem: Ordem) => {
			void enviar(ordem, { status: "EM_CAMPO" }).then(
				() => {
					setErroEnvio(null);
					setMensagem(`OI #${ordem.id} enviada a campo.`);
				},
				(error: unknown) => {
					setErroEnvio(
						mensagemErroOrdem(
							error,
							`Não foi possível enviar a OI #${ordem.id} a campo.`,
						),
					);
				},
			);
		},
		[enviar],
	);

	const envio = useEnvioAdiado(enviarACampo);
	const { agendar } = envio;

	const abrir = useCallback(
		(acao: AcaoOrdem, ordem: Ordem) => {
			if (acao === "enviar") {
				agendar(ordem);
				setMensagem(
					`OI #${ordem.id} vai a campo em alguns segundos. Use Desfazer no aviso para cancelar.`,
				);
				return;
			}
			setPainel({ tipo: acao, ordem, open: true });
		},
		[agendar],
	);

	const abrirHistorico = useCallback((ordem: Ordem) => {
		setPainel({ tipo: "historico", ordem, open: true });
	}, []);

	const pendente = useCallback(
		(id: number) =>
			pendentes.has(id) || envio.agendados.some((a) => a.ordem.id === id),
		[pendentes, envio.agendados],
	);

	const contexto = useMemo(
		() => ({ abrir, abrirHistorico, pendente }),
		[abrir, abrirHistorico, pendente],
	);

	const aoMudarAbertura = (tipo: TipoPainel, open: boolean) =>
		setPainel((prev) =>
			prev && prev.tipo === tipo ? { ...prev, open } : prev,
		);

	const concluida = (ordem: Ordem) => {
		setErroEnvio(null);
		setMensagem(`OI #${ordem.id} concluída.`);
		setPainel((prev) => (prev ? { ...prev, open: false } : prev));
	};

	const cancelada = (ordem: Ordem) => {
		setErroEnvio(null);
		setMensagem(`OI #${ordem.id} cancelada.`);
		setPainel((prev) => (prev ? { ...prev, open: false } : prev));
	};

	return (
		<AcoesOrdemContext value={contexto}>
			{children}
			<ConcluirOrdemModal
				ordem={painel?.ordem ?? null}
				open={Boolean(painel?.tipo === "concluir" && painel.open)}
				onOpenChange={(open) => aoMudarAbertura("concluir", open)}
				onConcluida={concluida}
				onEnviar={enviar}
			/>
			<CancelarOrdemModal
				ordem={painel?.ordem ?? null}
				open={Boolean(painel?.tipo === "cancelar" && painel.open)}
				onOpenChange={(open) => aoMudarAbertura("cancelar", open)}
				onCancelada={cancelada}
				onEnviar={enviar}
			/>
			<HistoricoOrdemSheet
				ordem={painel?.ordem ?? null}
				open={Boolean(painel?.tipo === "historico" && painel.open)}
				onOpenChange={(open) => aoMudarAbertura("historico", open)}
			/>
			<output aria-live="polite" className="sr-only">
				{mensagem}
			</output>
			{(envio.agendados.length > 0 || erroEnvio) && (
				// Embaixo e no centro: o canto direito é do botão do TanStack Devtools em dev.
				<div className="fixed bottom-4 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-96 -translate-x-1/2 flex-col gap-2">
					{envio.agendados.map((agendado) => {
						const { id } = agendado.ordem;
						return (
							<AvisoEnvioAdiado
								key={id}
								agendado={agendado}
								onDesfazer={() => {
									envio.desfazer(id);
									setMensagem(`Envio da OI #${id} desfeito.`);
								}}
								onEnviarAgora={() => envio.enviarAgora(id)}
								onPausar={() => envio.pausar(id)}
								onRetomar={() => envio.retomar(id)}
							/>
						);
					})}
					{erroEnvio && (
						<div
							role="alert"
							className="flex flex-col gap-2 rounded-lg border border-border-strong bg-surface-2 p-3 shadow-overlay"
						>
							<p className="text-body text-text">{erroEnvio}</p>
							<div className="flex justify-end">
								<Button
									size="sm"
									variant="ghost"
									aria-label="Fechar aviso"
									onClick={() => setErroEnvio(null)}
								>
									Fechar
								</Button>
							</div>
						</div>
					)}
				</div>
			)}
		</AcoesOrdemContext>
	);
}
