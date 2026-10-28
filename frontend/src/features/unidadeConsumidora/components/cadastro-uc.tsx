import { formatData, formatKWh, formatNumero } from "#/lib/format";
import type { Uc360 } from "../types";

const tipos = {
	eletromecanico: "Eletromecânico",
	eletronico: "Eletrônico",
	smart: "Smart",
};
const modalidades = {
	geracao_propria_uc: "Geração própria na UC",
	autoconsumo_remoto: "Autoconsumo remoto",
	geracao_compartilhada: "Geração compartilhada",
};

export function CadastroUc({
	cadastro,
	medidor,
}: Pick<Uc360, "cadastro" | "medidor">) {
	return (
		<aside className="min-w-0 rounded-md border border-border bg-surface-1 px-4">
			<section aria-labelledby="uc-cadastro" className="py-4">
				<h2 id="uc-cadastro" className="text-heading">
					Cadastro
				</h2>
				<dl className="mt-4 grid gap-3 text-body [&_dt]:text-small [&_dt]:text-text-muted [&_dd]:mt-1 [&_dd]:break-words">
					<div>
						<dt>Documento</dt>
						<dd className="font-mono">
							{cadastro.documento_mascarado ?? "Não informado"}
						</dd>
					</div>
					<div>
						<dt>Classe tarifária</dt>
						<dd>{cadastro.classe}</dd>
					</div>
					<div>
						<dt>Alimentador</dt>
						<dd className="font-mono">{cadastro.cod_alimentador}</dd>
					</div>
					<div>
						<dt>Data de ligação</dt>
						<dd className="tabular-nums">
							{formatData(cadastro.data_ligacao)}
						</dd>
					</div>
					<div>
						<dt>Média de consumo da Gold · 12 meses</dt>
						<dd className="font-mono tabular-nums">
							{cadastro.consumo_medio_kwh_12m == null
								? "Não informado"
								: formatKWh(cadastro.consumo_medio_kwh_12m)}
						</dd>
					</div>
				</dl>
			</section>
			<section
				aria-labelledby="uc-medidor"
				className="border-border border-t py-4"
			>
				<h2 id="uc-medidor" className="text-heading">
					Medidor
				</h2>
				{medidor ? (
					<dl className="mt-4 grid grid-cols-2 gap-3 text-body [&_dt]:text-small [&_dt]:text-text-muted [&_dd]:mt-1 [&_dd]:break-words">
						<div className="col-span-2">
							<dt>Código</dt>
							<dd className="font-mono">{medidor.cod_medidor}</dd>
						</div>
						<div>
							<dt>Tipo</dt>
							<dd>{tipos[medidor.tipo_medidor]}</dd>
						</div>
						<div>
							<dt>Modelo</dt>
							<dd>{medidor.modelo ?? "Não informado"}</dd>
						</div>
						<div>
							<dt>Instalação</dt>
							<dd className="tabular-nums">
								{formatData(medidor.data_instalacao)}
							</dd>
						</div>
						<div>
							<dt>Idade informada</dt>
							<dd className="font-mono tabular-nums">
								{formatNumero(medidor.idade_anos)} anos
							</dd>
						</div>
						<div>
							<dt>Trocas</dt>
							<dd className="font-mono tabular-nums">
								{formatNumero(medidor.n_trocas)}
							</dd>
						</div>
						<div className="col-span-2">
							<dt>Última troca</dt>
							<dd>
								{medidor.data_ultima_troca
									? formatData(medidor.data_ultima_troca)
									: "Sem troca registrada"}
							</dd>
						</div>
					</dl>
				) : (
					<p className="mt-3 text-body text-text-muted">
						Medidor não informado na base.
					</p>
				)}
			</section>
			<section aria-labelledby="uc-gd" className="border-border border-t py-4">
				<h2 id="uc-gd" className="text-heading">
					Geração distribuída
				</h2>
				<p className="mt-3 text-body">
					{cadastro.possui_gd
						? "Com geração distribuída"
						: "Sem geração distribuída cadastrada"}
				</p>
				{cadastro.possui_gd && (
					<>
						<dl className="mt-4 grid gap-3 text-body [&_dt]:text-small [&_dt]:text-text-muted [&_dd]:mt-1">
							<div>
								<dt>Modalidade</dt>
								<dd>
									{cadastro.modalidade_gd
										? modalidades[cadastro.modalidade_gd]
										: "Não informado"}
								</dd>
							</div>
							<div>
								<dt>Potência</dt>
								<dd className="font-mono tabular-nums">
									{cadastro.potencia_kwp == null
										? "Não informado"
										: `${formatNumero(cadastro.potencia_kwp)} kWp`}
								</dd>
							</div>
							<div>
								<dt>Conexão</dt>
								<dd>
									{cadastro.data_conexao_gd
										? formatData(cadastro.data_conexao_gd)
										: "Não informado"}
								</dd>
							</div>
							<div>
								<dt>Energia injetada mensal informada</dt>
								<dd className="font-mono tabular-nums">
									{cadastro.energia_injetada_kwh_mes == null
										? "Não informado"
										: formatKWh(cadastro.energia_injetada_kwh_mes)}
								</dd>
							</div>
						</dl>
						<p className="mt-4 text-small text-text-muted">
							Energia faturada não representa necessariamente todo o consumo do
							imóvel.
						</p>
					</>
				)}
			</section>
		</aside>
	);
}
