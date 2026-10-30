import { ArrowsClockwiseIcon, CircleNotchIcon } from "@phosphor-icons/react";
import { type DragEvent, useMemo, useState } from "react";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { formatDataHora } from "#/lib/format";
import { cn } from "#/lib/utils";
import {
	ACAO_ORDEM_ROTULO,
	acaoParaDestino,
	agruparOrdensKanban,
	RESULTADO_ORDEM_ROTULO,
	STATUS_ORDEM_VISUAL,
} from "../conversions";
import { useLimiteFinalizadas } from "../hooks/use-limite-finalizadas";
import {
	type AcaoOrdem,
	type Ordem,
	STATUS_ORDEM,
	type StatusOrdem,
} from "../types";
import { OrdemAcoesBotoes } from "./ordem-acoes-botoes";

// Ocupa a área toda da tela: `flex-1` preenche a altura que sobra na página, e as colunas
// esticam junto (alvo de soltar até o fim da tela, mesmo com poucas OIs).
const GRADE =
	"grid min-h-[28rem] flex-1 grid-flow-col auto-cols-[minmax(17rem,1fr)] gap-3 overflow-x-auto pb-2";

const VER_TODAS_ROTULO: Record<"CONCLUIDA" | "CANCELADA", string> = {
	CONCLUIDA: "Ver todas as ordens concluídas",
	CANCELADA: "Ver todas as ordens canceladas",
};

/** `true` para as colunas que cortam a lista e oferecem "Ver todas". */
function finalizada(status: StatusOrdem): status is "CONCLUIDA" | "CANCELADA" {
	return status === "CONCLUIDA" || status === "CANCELADA";
}

/**
 * Quadro das OIs. Apresentacional: recebe a lista completa e os callbacks; quem executa as
 * ações é o controlador da página. Arrastar um cartão é atalho para a mesma ação dos botões.
 */
export function OrdensKanban({
	ordens,
	loading,
	error,
	onRetry,
	onAcao,
	onHistorico,
	pendente,
	onVerTodas,
}: {
	ordens: Ordem[] | undefined;
	loading: boolean;
	error: string | null;
	onRetry: () => void;
	onAcao: (acao: AcaoOrdem, ordem: Ordem) => void;
	onHistorico: (ordem: Ordem) => void;
	pendente: (id: number) => boolean;
	onVerTodas: (status: "CONCLUIDA" | "CANCELADA") => void;
}) {
	const limite = useLimiteFinalizadas();
	const grupos = useMemo(
		() => agruparOrdensKanban(ordens ?? [], limite),
		[ordens, limite],
	);
	const [arrastando, setArrastando] = useState<Ordem | null>(null);
	const [colunaAlvo, setColunaAlvo] = useState<StatusOrdem | null>(null);

	const colunas: Record<StatusOrdem, { cartoes: Ordem[]; total: number }> = {
		GERADA: { cartoes: grupos.GERADA, total: grupos.GERADA.length },
		EM_CAMPO: { cartoes: grupos.EM_CAMPO, total: grupos.EM_CAMPO.length },
		CONCLUIDA: {
			cartoes: grupos.CONCLUIDA.visiveis,
			total: grupos.CONCLUIDA.total,
		},
		CANCELADA: {
			cartoes: grupos.CANCELADA.visiveis,
			total: grupos.CANCELADA.total,
		},
	};

	if (loading && ordens === undefined) {
		return (
			<div aria-busy="true" className={GRADE}>
				{STATUS_ORDEM.map((status) => {
					const { rotulo, ponto } = STATUS_ORDEM_VISUAL[status];
					return (
						<section
							key={status}
							aria-label={rotulo}
							className="flex flex-col gap-2 rounded-lg border border-border bg-surface-1 p-2"
						>
							<header className="flex items-center gap-2 px-1">
								<span
									aria-hidden
									className={cn("size-2 rounded-full", ponto)}
								/>
								<h3 className="text-body font-medium">{rotulo}</h3>
							</header>
							<ul className="flex flex-col gap-2" aria-hidden>
								{[0, 1].map((indice) => (
									<li
										key={indice}
										className="h-28 rounded-md bg-surface-2 animate-pulse motion-reduce:animate-none"
									/>
								))}
							</ul>
						</section>
					);
				})}
			</div>
		);
	}

	if (error) {
		return (
			<div
				role="alert"
				className="flex flex-col items-center gap-3 rounded-lg border border-border bg-surface-1 p-6 text-center"
			>
				<p className="text-body">{error}</p>
				<Button variant="outline" size="sm" onClick={onRetry}>
					<ArrowsClockwiseIcon aria-hidden />
					Tentar de novo
				</Button>
			</div>
		);
	}

	return (
		<div className={GRADE}>
			{STATUS_ORDEM.map((status) => (
				<ColunaKanban
					key={status}
					status={status}
					cartoes={colunas[status].cartoes}
					total={colunas[status].total}
					limite={limite}
					arrastando={arrastando}
					destacada={colunaAlvo === status}
					pendente={pendente}
					onAcao={onAcao}
					onHistorico={onHistorico}
					onVerTodas={onVerTodas}
					onDestacar={setColunaAlvo}
					onIniciarArraste={setArrastando}
					onFinalizarArraste={() => {
						setArrastando(null);
						setColunaAlvo(null);
					}}
					onSoltar={(destino) => {
						if (!arrastando) return;
						const acao = acaoParaDestino(arrastando.status, destino);
						if (!acao) return;
						onAcao(acao, arrastando);
						setArrastando(null);
						setColunaAlvo(null);
					}}
				/>
			))}
		</div>
	);
}

function ColunaKanban({
	status,
	cartoes,
	total,
	limite,
	arrastando,
	destacada,
	pendente,
	onAcao,
	onHistorico,
	onVerTodas,
	onDestacar,
	onIniciarArraste,
	onFinalizarArraste,
	onSoltar,
}: {
	status: StatusOrdem;
	cartoes: Ordem[];
	total: number;
	limite: number;
	arrastando: Ordem | null;
	destacada: boolean;
	pendente: (id: number) => boolean;
	onAcao: (acao: AcaoOrdem, ordem: Ordem) => void;
	onHistorico: (ordem: Ordem) => void;
	onVerTodas: (status: "CONCLUIDA" | "CANCELADA") => void;
	onDestacar: (status: StatusOrdem | null) => void;
	onIniciarArraste: (ordem: Ordem) => void;
	onFinalizarArraste: () => void;
	onSoltar: (status: StatusOrdem) => void;
}) {
	const { rotulo, ponto } = STATUS_ORDEM_VISUAL[status];
	const idTitulo = `kanban-titulo-${status.toLowerCase()}`;
	const acao = arrastando ? acaoParaDestino(arrastando.status, status) : null;
	const aceita = acao !== null;
	const esmaecida = arrastando !== null && !aceita;

	function aoArrastarSobre(event: DragEvent<HTMLElement>) {
		if (!arrastando) return;
		if (!aceita) {
			if (destacada) onDestacar(null);
			return;
		}
		event.preventDefault();
		event.dataTransfer.dropEffect = "move";
		onDestacar(status);
	}

	function aoSairDaColuna(event: DragEvent<HTMLElement>) {
		const alvo = event.relatedTarget;
		if (alvo instanceof Node && event.currentTarget.contains(alvo)) return;
		if (destacada) onDestacar(null);
	}

	return (
		<section
			aria-labelledby={idTitulo}
			onDragOver={aoArrastarSobre}
			onDragLeave={aoSairDaColuna}
			onDrop={(event) => {
				if (!aceita) return;
				event.preventDefault();
				onSoltar(status);
			}}
			className={cn(
				"flex flex-col gap-3 rounded-lg border bg-surface-1 p-3",
				destacada
					? "border-accent border-dashed bg-accent-subtle"
					: "border-border",
			)}
		>
			<header className="flex items-center gap-2 px-1">
				<span aria-hidden className={cn("size-2 rounded-full", ponto)} />
				<h3
					id={idTitulo}
					className={cn(
						"text-body font-medium",
						esmaecida && "text-text-disabled",
					)}
				>
					{rotulo}
					<span className="sr-only">
						, {total} {total === 1 ? "ordem" : "ordens"}
					</span>
				</h3>
				<Badge
					className={cn(
						"ml-auto tabular-nums",
						esmaecida && "text-text-disabled",
					)}
				>
					{total}
				</Badge>
			</header>

			{destacada && acao && (
				<output className="block rounded-md border border-dashed border-accent px-2 py-1 text-small text-accent-text">
					Solte para {ACAO_ORDEM_ROTULO[acao].toLowerCase()}
				</output>
			)}

			<ul className="flex flex-col gap-2">
				{cartoes.length === 0 ? (
					<li className="flex min-h-28 items-center justify-center text-small text-text-muted">
						Nenhuma OI
					</li>
				) : (
					cartoes.map((ordem) => (
						<CartaoKanban
							key={ordem.id}
							ordem={ordem}
							pendente={pendente(ordem.id)}
							onAcao={onAcao}
							onHistorico={onHistorico}
							onIniciarArraste={onIniciarArraste}
							onFinalizarArraste={onFinalizarArraste}
						/>
					))
				)}
			</ul>

			{finalizada(status) && total > limite && (
				<footer className="mt-auto flex flex-col items-start gap-1 px-1 pt-1">
					<p className="text-small text-text-muted tabular-nums">
						Mostrando {cartoes.length} de {total}
					</p>
					<Button
						variant="link"
						size="sm"
						className="h-auto px-0"
						aria-label={VER_TODAS_ROTULO[status]}
						onClick={() => onVerTodas(status)}
					>
						Ver todas
					</Button>
				</footer>
			)}
		</section>
	);
}

function CartaoKanban({
	ordem,
	pendente,
	onAcao,
	onHistorico,
	onIniciarArraste,
	onFinalizarArraste,
}: {
	ordem: Ordem;
	pendente: boolean;
	onAcao: (acao: AcaoOrdem, ordem: Ordem) => void;
	onHistorico: (ordem: Ordem) => void;
	onIniciarArraste: (ordem: Ordem) => void;
	onFinalizarArraste: () => void;
}) {
	const ativa = ordem.status === "GERADA" || ordem.status === "EM_CAMPO";
	const arrastavel = ativa && !pendente;

	return (
		<li
			draggable={arrastavel}
			aria-busy={pendente || undefined}
			onDragStart={(event) => {
				if (!arrastavel) return;
				event.dataTransfer.setData("text/plain", String(ordem.id));
				event.dataTransfer.effectAllowed = "move";
				onIniciarArraste(ordem);
			}}
			onDragEnd={onFinalizarArraste}
			className={cn(
				"flex flex-col gap-3 rounded-md border border-border bg-surface-2 p-4",
				"transition-[translate,background-color,border-color,box-shadow] duration-150 ease-out hover:-translate-y-0.5 hover:border-border-strong hover:bg-surface-2 hover:shadow-overlay focus-within:border-border-strong focus-within:bg-surface-2 focus-within:shadow-overlay motion-reduce:transition-none motion-reduce:hover:translate-y-0",
				arrastavel && "cursor-grab active:cursor-grabbing",
			)}
		>
			<p className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
				<span className="font-medium tabular-nums">OI #{ordem.id}</span>
				<span className="text-text-muted tabular-nums">UC {ordem.cod_uc}</span>
				{pendente && (
					<CircleNotchIcon
						aria-hidden
						className="size-4 animate-spin text-text-muted motion-reduce:animate-none"
					/>
				)}
			</p>

			<p className="text-small text-text-muted">
				{ativa ? "Criada em " : "Atualizada em "}
				{formatDataHora(ativa ? ordem.criada_em : ordem.atualizada_em)}
			</p>

			{ordem.status === "CONCLUIDA" && ordem.resultado && (
				<Badge className="self-start">
					{RESULTADO_ORDEM_ROTULO[ordem.resultado]}
				</Badge>
			)}

			{ordem.observacao && (
				<p
					className="line-clamp-2 text-small text-text-muted"
					title={ordem.observacao}
				>
					{ordem.observacao}
				</p>
			)}

			<OrdemAcoesBotoes
				ordem={ordem}
				onAcao={onAcao}
				onHistorico={onHistorico}
				pendente={pendente}
				className="mt-auto"
			/>
		</li>
	);
}
