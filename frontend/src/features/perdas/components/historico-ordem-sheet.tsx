import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "#/components/ui/sheet";
import { ApiError } from "#/lib/api";
import { formatDataHora } from "#/lib/format";
import {
	RESULTADO_ORDEM_ROTULO,
	STATUS_ORDEM_VISUAL,
	tituloEvento,
} from "../conversions";
import { useOrdem } from "../hooks/use-ordem";
import type { Ordem } from "../types";

function ResumoOrdem({
	status,
	resultado,
	observacao,
}: {
	status: Ordem["status"];
	resultado: Ordem["resultado"];
	observacao: string | null;
}) {
	const { rotulo, ponto } = STATUS_ORDEM_VISUAL[status];
	return (
		<div className="flex flex-col gap-2">
			<div className="flex flex-wrap items-center gap-2">
				<Badge>
					<span
						data-icon="inline-start"
						aria-hidden
						className={`size-1.5 rounded-full ${ponto}`}
					/>
					{rotulo}
				</Badge>
				{resultado && (
					<span className="text-body text-text">
						{RESULTADO_ORDEM_ROTULO[resultado]}
					</span>
				)}
			</div>
			{observacao && <p className="text-body text-text-muted">{observacao}</p>}
		</div>
	);
}

export function HistoricoOrdemSheet({
	ordem,
	open,
	onOpenChange,
}: {
	ordem: Ordem | null;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}) {
	const { data, isPending, isError, error, refetch } = useOrdem(
		open ? (ordem?.id ?? null) : null,
	);
	const naoEncontrada = error instanceof ApiError && error.status === 404;

	return (
		<Sheet open={open} onOpenChange={onOpenChange}>
			<SheetContent>
				<SheetHeader>
					<SheetTitle>OI #{ordem?.id}</SheetTitle>
					<SheetDescription>UC {ordem?.cod_uc}</SheetDescription>
				</SheetHeader>
				<div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
					{open && isPending && (
						<div aria-hidden className="flex flex-col gap-4">
							{Array.from({ length: 3 }, (_, i) => (
								<div
									// biome-ignore lint/suspicious/noArrayIndexKey: blocos fixos do molde.
									key={i}
									className="flex flex-col gap-2"
								>
									<div className="h-3 w-2/5 animate-pulse rounded-sm bg-pressed motion-reduce:animate-none" />
									<div className="h-2 w-1/3 animate-pulse rounded-sm bg-pressed motion-reduce:animate-none" />
								</div>
							))}
						</div>
					)}
					{isError && (
						<div className="flex flex-col items-start gap-3">
							<p className="text-body text-text" role="alert">
								{naoEncontrada
									? `OI #${ordem?.id} não encontrada.`
									: "Não foi possível carregar o histórico da OI."}
							</p>
							{!naoEncontrada && (
								<Button
									variant="outline"
									size="sm"
									onClick={() => void refetch()}
								>
									Tentar de novo
								</Button>
							)}
						</div>
					)}
					{data && (
						<>
							<ResumoOrdem
								status={data.status}
								resultado={data.resultado}
								observacao={data.observacao}
							/>
							<ol
								aria-label={`Histórico da OI ${data.id}`}
								className="flex flex-col"
							>
								{data.eventos.map((evento, indice) => {
									const { origem, destino } = tituloEvento(evento);
									return (
										<li
											// biome-ignore lint/suspicious/noArrayIndexKey: eventos sem id próprio na API.
											key={`${evento.ocorrido_em}-${indice}`}
											className="flex gap-3 pb-4 last:pb-0"
										>
											<span
												aria-hidden
												className="mt-1.5 size-1.5 shrink-0 rounded-full bg-border-strong"
											/>
											<div className="flex min-w-0 flex-col gap-0.5">
												<p className="text-body text-text">
													{origem ? (
														<>
															{origem} <span aria-hidden>→</span>
															<span className="sr-only"> para </span>
															{destino}
														</>
													) : (
														`Criada como ${destino}`
													)}
												</p>
												<time
													dateTime={evento.ocorrido_em}
													className="text-small text-text-muted"
												>
													{formatDataHora(evento.ocorrido_em)}
												</time>
												{evento.observacao && (
													<p className="text-body text-text-muted">
														{evento.observacao}
													</p>
												)}
											</div>
										</li>
									);
								})}
							</ol>
						</>
					)}
				</div>
			</SheetContent>
		</Sheet>
	);
}
