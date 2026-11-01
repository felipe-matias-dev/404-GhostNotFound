import { DownloadSimpleIcon, UploadSimpleIcon } from "@phosphor-icons/react";
import { useRef, useState } from "react";
import { Button } from "#/components/ui/button";
import { Modal } from "#/components/ui/modal";
import { baixarPlanilhaCampo } from "../api";
import { mensagemErroOrdem } from "../conversions";
import { useEnviarPlanilha } from "../hooks/use-enviar-planilha";
import type { ResultadoPlanilha } from "../types";

const NOME_ARQUIVO = "ordens-em-campo.xlsx";

function plural(quantidade: number, singular: string, pluralForma: string) {
	return `${quantidade} ${quantidade === 1 ? singular : pluralForma}`;
}

export function PlanilhaCampo() {
	const [baixando, setBaixando] = useState(false);
	const [erroDownload, setErroDownload] = useState<string | null>(null);
	const [aberto, setAberto] = useState(false);
	const [arquivo, setArquivo] = useState<File | null>(null);
	const [resultado, setResultado] = useState<ResultadoPlanilha | null>(null);
	const [erroEnvio, setErroEnvio] = useState<string | null>(null);
	const entrada = useRef<HTMLInputElement>(null);
	const enviar = useEnviarPlanilha();

	async function baixar() {
		setErroDownload(null);
		setBaixando(true);
		try {
			const url = URL.createObjectURL(await baixarPlanilhaCampo());
			const link = document.createElement("a");
			link.href = url;
			link.download = NOME_ARQUIVO;
			link.click();
			URL.revokeObjectURL(url);
		} catch (error) {
			setErroDownload(
				mensagemErroOrdem(error, "Não foi possível baixar a planilha."),
			);
		} finally {
			setBaixando(false);
		}
	}

	function abrir() {
		setArquivo(null);
		setResultado(null);
		setErroEnvio(null);
		enviar.reset();
		setAberto(true);
	}

	function aoEnviar() {
		if (!arquivo) return;
		setErroEnvio(null);
		enviar.mutate(arquivo, {
			onSuccess: setResultado,
			onError: (error) =>
				setErroEnvio(
					mensagemErroOrdem(error, "Não foi possível enviar a planilha."),
				),
		});
	}

	const enviando = enviar.isPending;

	return (
		<>
			<Button
				variant="outline"
				size="sm"
				disabled={baixando}
				onClick={() => void baixar()}
			>
				<DownloadSimpleIcon aria-hidden />
				{baixando ? "Baixando…" : "Baixar planilha de campo"}
			</Button>
			<Button variant="outline" size="sm" onClick={abrir}>
				<UploadSimpleIcon aria-hidden />
				Enviar planilha de campo
			</Button>
			{erroDownload && (
				<p role="alert" className="text-small text-danger">
					{erroDownload}
				</p>
			)}
			<Modal
				open={aberto}
				onClose={() => {
					if (!enviando) setAberto(false);
				}}
				closeOnEscape={!enviando}
				closeOnBackdrop={!enviando}
				title="Enviar planilha de campo"
				description="Suba o Excel que a equipe preencheu. Só as OIs em campo são concluídas; as demais linhas voltam com o motivo."
				maxWidth={640}
				footer={
					<>
						<Button
							type="button"
							variant="ghost"
							disabled={enviando}
							onClick={() => setAberto(false)}
						>
							{resultado ? "Fechar" : "Voltar"}
						</Button>
						{!resultado && (
							<Button
								type="button"
								disabled={!arquivo || enviando}
								onClick={aoEnviar}
							>
								{enviando ? "Enviando…" : "Enviar"}
							</Button>
						)}
					</>
				}
			>
				<div className="flex flex-col gap-4">
					{!resultado && (
						<div className="flex flex-col gap-1.5">
							<label htmlFor="planilha-campo-arquivo" className="text-small">
								Arquivo (.xlsx, até 5 MB)
							</label>
							<input
								id="planilha-campo-arquivo"
								ref={entrada}
								type="file"
								accept=".xlsx"
								disabled={enviando}
								onChange={(evento) =>
									setArquivo(evento.target.files?.[0] ?? null)
								}
								className="text-body text-text file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-border-strong file:bg-surface-1 file:px-3 file:py-1.5 file:text-body file:text-text"
							/>
						</div>
					)}
					{erroEnvio && (
						<p
							role="alert"
							className="rounded-md bg-danger-subtle px-3 py-2 text-body text-danger"
						>
							{erroEnvio}
						</p>
					)}
					{resultado && <RelatorioPlanilha resultado={resultado} />}
				</div>
			</Modal>
		</>
	);
}

function RelatorioPlanilha({ resultado }: { resultado: ResultadoPlanilha }) {
	const { concluidas, rejeitadas, linhas_lidas } = resultado;
	return (
		<div className="flex flex-col gap-3" aria-live="polite">
			<p className="text-body text-text">
				{plural(linhas_lidas, "linha lida", "linhas lidas")}:{" "}
				<strong>
					{plural(concluidas.length, "OI concluída", "OIs concluídas")}
				</strong>
				, {plural(rejeitadas.length, "rejeitada", "rejeitadas")}.
			</p>
			{rejeitadas.length > 0 && (
				<div className="max-h-64 overflow-auto rounded-md border border-border">
					<table className="w-full text-left text-small">
						<thead className="sticky top-0 bg-surface-2 text-text-muted">
							<tr>
								<th className="px-3 py-2 font-medium">Aba</th>
								<th className="px-3 py-2 font-medium">Linha</th>
								<th className="px-3 py-2 font-medium">UC</th>
								<th className="px-3 py-2 font-medium">Motivo</th>
							</tr>
						</thead>
						<tbody>
							{rejeitadas.map((linha) => (
								<tr
									key={`${linha.aba}-${linha.linha}`}
									className="border-t border-border align-top"
								>
									<td className="px-3 py-2">{linha.aba}</td>
									<td className="px-3 py-2">{linha.linha}</td>
									<td className="px-3 py-2 font-mono">{linha.cod_uc ?? "—"}</td>
									<td className="px-3 py-2">{linha.motivo}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			)}
		</div>
	);
}
