import { FunnelIcon } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { type ReactNode, useId, useState } from "react";
import { Button, buttonVariants } from "#/components/ui/button";
import { Checkbox } from "#/components/ui/checkbox";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "#/components/ui/popover";
import { distribuicaoQueda, filaKey } from "../api";
import { FILTROS_FILA_INICIAIS, type FiltrosFila } from "../types";

export function FiltrosSuspeitas({
	value,
	onChange,
	disabled,
}: {
	value: FiltrosFila;
	onChange: (value: FiltrosFila) => void;
	disabled: boolean;
}) {
	const [aberto, setAberto] = useState(false);
	const [rascunho, setRascunho] = useState(value);
	const medidorId = useId();
	const { data, isPending, isError, refetch } = useQuery({
		queryKey: [...filaKey, "distribuicao-queda"],
		queryFn: distribuicaoQueda,
	});
	const bins = Array.from({ length: 21 }, (_, index) => ({
		inicio: index * 5,
		total:
			data?.itens.reduce(
				(sum, item) =>
					Math.floor(item.queda / 5) === index ? sum + item.total : sum,
				0,
			) ?? 0,
	}));
	const maior = Math.max(1, ...bins.map((bin) => bin.total));
	const ativos =
		Number(value.queda !== null) +
		Number(value.medidorEletromecanico) +
		Number(value.leiturasEstimadas !== null);
	const [min, max] = rascunho.queda ?? [0, 100];

	return (
		<Popover
			open={aberto}
			onOpenChange={(open) => {
				if (open) setRascunho(value);
				setAberto(open);
			}}
		>
			<PopoverTrigger
				disabled={disabled}
				className={buttonVariants({
					variant: ativos ? "secondary" : "outline",
					size: "sm",
				})}
			>
				<FunnelIcon aria-hidden />
				Filtros
				{ativos > 0 && (
					<span className="rounded-sm bg-accent-subtle px-1.5 text-small text-accent-text">
						{ativos}
						<span className="sr-only">
							{ativos === 1 ? " filtro ativo" : " filtros ativos"}
						</span>
					</span>
				)}
			</PopoverTrigger>
			<PopoverContent
				align="end"
				aria-label="Filtros da fila de suspeitas"
				className="max-h-(--available-height) w-80 max-w-[calc(100vw-1.5rem)] overflow-y-auto"
			>
				<form
					onSubmit={(event) => {
						event.preventDefault();
						onChange(rascunho);
						setAberto(false);
					}}
				>
					<fieldset disabled={disabled} className="grid gap-1 p-1">
						<legend className="sr-only">Sinais da suspeita</legend>
						<FaixaPercentual
							label="Queda no consumo"
							value={rascunho.queda}
							disabled={disabled}
							onChange={(queda) => setRascunho({ ...rascunho, queda })}
						>
							<DistribuicaoQueda
								bins={bins}
								maior={maior}
								min={min}
								max={max}
								isPending={isPending}
								isError={isError}
								onRetry={() => refetch()}
							/>
						</FaixaPercentual>
						{rascunho.queda !== null && data?.sem_queda_identificada ? (
							<p className="px-2 pb-2 text-small text-text-muted">
								{data.sem_queda_identificada} UCs sem queda identificada ficam
								fora ao filtrar por queda.
							</p>
						) : null}
						<label
							htmlFor={medidorId}
							className="flex min-h-8 cursor-pointer items-center gap-2 rounded-sm px-2 text-body hover:bg-hover"
						>
							<Checkbox
								id={medidorId}
								label="Somente medidor eletromecânico"
								checked={rascunho.medidorEletromecanico}
								disabled={disabled}
								onChange={(medidorEletromecanico) =>
									setRascunho({ ...rascunho, medidorEletromecanico })
								}
							/>
							Somente medidor eletromecânico
						</label>
						<div className="grid gap-1">
							<FaixaPercentual
								label="Leituras estimadas"
								value={rascunho.leiturasEstimadas}
								disabled={disabled}
								onChange={(leiturasEstimadas) =>
									setRascunho({ ...rascunho, leiturasEstimadas })
								}
							/>
							{rascunho.leiturasEstimadas !== null && (
								<p className="px-2 pb-2 text-small text-text-muted">
									Nas 12 últimas competências. Percentuais não informados ficam
									fora ao filtrar.
								</p>
							)}
						</div>
					</fieldset>
					<div className="sticky bottom-0 flex items-center justify-between gap-2 border-t border-border bg-surface-2 p-2">
						<Button
							type="button"
							variant="ghost"
							size="sm"
							disabled={disabled}
							onClick={() => {
								setRascunho(FILTROS_FILA_INICIAIS);
								onChange(FILTROS_FILA_INICIAIS);
							}}
						>
							Limpar filtros
						</Button>
						<Button type="submit" size="sm" disabled={disabled}>
							Aplicar filtros
						</Button>
					</div>
				</form>
			</PopoverContent>
		</Popover>
	);
}

function FaixaPercentual({
	label,
	value,
	onChange,
	disabled,
	children,
}: {
	label: string;
	value: [number, number] | null;
	onChange: (value: [number, number] | null) => void;
	disabled: boolean;
	children?: ReactNode;
}) {
	const [min, max] = value ?? [0, 100];
	const id = useId();
	return (
		<fieldset className="grid gap-1">
			<legend className="sr-only">{label}</legend>
			<label
				htmlFor={id}
				className="flex min-h-8 cursor-pointer items-center gap-2 rounded-sm px-2 text-body hover:bg-hover"
			>
				<Checkbox
					id={id}
					label={label}
					checked={value !== null}
					disabled={disabled}
					onChange={(checked) => onChange(checked ? [0, 100] : null)}
				/>
				{label}
			</label>
			{value !== null && (
				<div className="grid grid-cols-2 gap-3 px-2 pb-2">
					{(["Mínima", "Máxima"] as const).map((limite, index) => (
						<label
							key={limite}
							className="grid gap-2 text-small text-text-muted"
						>
							<span className="flex justify-between gap-2">
								{limite}
								<span className="tabular-nums text-text">
									{index === 0 ? min : max}%
								</span>
							</span>
							<input
								aria-label={`${label}: ${limite.toLowerCase()}`}
								type="range"
								min={0}
								max={100}
								value={index === 0 ? min : max}
								onChange={(event) => {
									const numero = Number(event.target.value);
									onChange(
										index === 0
											? [Math.min(numero, max), max]
											: [min, Math.max(numero, min)],
									);
								}}
								className="w-full accent-accent"
							/>
						</label>
					))}
				</div>
			)}
			{value !== null && children}
		</fieldset>
	);
}

function DistribuicaoQueda({
	bins,
	maior,
	min,
	max,
	isPending,
	isError,
	onRetry,
}: {
	bins: { inicio: number; total: number }[];
	maior: number;
	min: number;
	max: number;
	isPending: boolean;
	isError: boolean;
	onRetry: () => void;
}) {
	return (
		<div className="grid gap-2 px-2 pb-2">
			<p className="text-small text-text-muted">
				Distribuição da queda na fila inteira
			</p>
			{isPending ? (
				<p className="text-small text-text-muted">Carregando distribuição…</p>
			) : isError ? (
				<div className="flex flex-wrap items-center gap-2 text-small">
					<span>Não foi possível carregar a distribuição.</span>
					<Button type="button" variant="ghost" size="sm" onClick={onRetry}>
						Tentar novamente
					</Button>
				</div>
			) : (
				<>
					<div className="flex h-12 items-end gap-1" aria-hidden="true">
						{bins.map((bin) => (
							<div
								key={bin.inicio}
								title={`${bin.inicio}–${Math.min(bin.inicio + 4, 100)}%: ${bin.total} UCs`}
								className={`min-w-0 flex-1 rounded-t-sm ${bin.inicio <= max && bin.inicio + 4 >= min ? "bg-accent" : "bg-border-strong"}`}
								style={{ height: `${(bin.total / maior) * 100}%` }}
							/>
						))}
					</div>
					<ul className="sr-only" aria-label="Distribuição por faixa de queda">
						{bins.map((bin) => (
							<li key={bin.inicio}>
								{bin.inicio} a {Math.min(bin.inicio + 4, 100)}%: {bin.total} UCs
							</li>
						))}
					</ul>
					<div className="flex justify-between text-small text-text-muted">
						<span>0%</span>
						<span>50%</span>
						<span>100%</span>
					</div>
				</>
			)}
		</div>
	);
}
