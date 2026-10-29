import { CalendarBlankIcon, CaretDownIcon } from "@phosphor-icons/react";
import { type FormEvent, type ReactElement, useId, useState } from "react";
import { Button } from "#/components/ui/button";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "#/components/ui/popover";
import { formatPeriodoCurto } from "#/lib/format";
import type { Periodo } from "../types";

const MES = /^\d{4}-(0[1-9]|1[0-2])$/;

const INCOMPLETO = "Informe os dois meses no formato AAAA-MM.";
const INVERTIDO = "O mês inicial deve ser anterior ou igual ao final.";

type Rascunho = { inicio: string; fim: string };

const doPeriodo = (periodo: Periodo | undefined): Rascunho => ({
	inicio: periodo?.inicio ?? "",
	fim: periodo?.fim ?? "",
});

function CampoMes({
	id,
	label,
	valor,
	invalid,
	descrito,
	onChange,
}: {
	id: string;
	label: string;
	valor: string;
	invalid: boolean;
	descrito: string | undefined;
	onChange: (valor: string) => void;
}) {
	return (
		<div className="flex min-w-0 flex-col gap-1">
			<label htmlFor={id} className="text-small text-text-muted">
				{label}
			</label>
			<input
				id={id}
				type="month"
				required
				value={valor}
				aria-invalid={invalid || undefined}
				aria-describedby={descrito}
				onChange={(evento) => onChange(evento.currentTarget.value)}
				className="h-8 w-full min-w-0 rounded-md border border-border-strong bg-surface-1 px-2 text-body text-text outline-none transition-colors focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 aria-invalid:border-danger aria-invalid:ring-danger/20"
			/>
		</div>
	);
}

export type IntervaloMesesProps = {
	periodo: Periodo | undefined;
	padrao: Periodo | undefined;
	onChange: (periodo: Periodo) => void;
};

/** Intervalo da tabela: dois meses nativos no popover, aplicados juntos ou não aplicados. */
export function IntervaloMeses({
	periodo,
	padrao,
	onChange,
}: IntervaloMesesProps): ReactElement {
	const id = useId();
	const erroId = `${id}-erro`;
	const [aberto, setAberto] = useState(false);
	const [rascunho, setRascunho] = useState<Rascunho>(() => doPeriodo(periodo));
	const [erro, setErro] = useState<string | null>(null);

	// O rascunho não vive fora do popover: cada abertura parte do período aplicado.
	const abrir = (proximo: boolean) => {
		setAberto(proximo);
		if (proximo) {
			setRascunho(doPeriodo(periodo));
			setErro(null);
		}
	};

	const aplicar = (escolhido: Periodo) => {
		onChange(escolhido);
		setAberto(false);
	};

	// `noValidate`: a mensagem é a da tela, não o balão nativo do navegador.
	const enviar = (evento: FormEvent<HTMLFormElement>) => {
		evento.preventDefault();
		if (!MES.test(rascunho.inicio) || !MES.test(rascunho.fim)) {
			setErro(INCOMPLETO);
			return;
		}
		if (rascunho.inicio > rascunho.fim) {
			setErro(INVERTIDO);
			return;
		}
		aplicar({ inicio: rascunho.inicio, fim: rascunho.fim });
	};

	const invalido = {
		inicio: erro === INCOMPLETO ? !MES.test(rascunho.inicio) : erro !== null,
		fim: erro === INCOMPLETO ? !MES.test(rascunho.fim) : erro !== null,
	};

	const rotulo = periodo
		? formatPeriodoCurto(`${periodo.inicio}/${periodo.fim}`)
		: "Escolher período";

	return (
		<Popover open={aberto} onOpenChange={abrir}>
			<PopoverTrigger
				aria-label={
					periodo
						? `Período da continuidade: ${rotulo}. Trocar`
						: "Escolher período da continuidade"
				}
				className="flex h-7 min-w-0 cursor-pointer items-center gap-1.5 rounded-md border border-border-strong px-2 text-small text-text-muted outline-none transition-colors hover:bg-hover hover:text-text focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover data-popup-open:text-text"
			>
				<CalendarBlankIcon aria-hidden className="size-3.5 shrink-0" />
				<span className="truncate">{rotulo}</span>
				<CaretDownIcon aria-hidden className="size-3 shrink-0" />
			</PopoverTrigger>
			<PopoverContent
				align="end"
				className="w-[21rem] max-w-[calc(100vw-1.5rem)] p-3"
			>
				<form noValidate onSubmit={enviar} className="flex flex-col gap-3">
					<div className="grid grid-cols-2 gap-2">
						<CampoMes
							id={`${id}-inicio`}
							label="De"
							valor={rascunho.inicio}
							invalid={invalido.inicio}
							descrito={erro ? erroId : undefined}
							onChange={(inicio) =>
								setRascunho((atual) => ({ ...atual, inicio }))
							}
						/>
						<CampoMes
							id={`${id}-fim`}
							label="Até"
							valor={rascunho.fim}
							invalid={invalido.fim}
							descrito={erro ? erroId : undefined}
							onChange={(fim) => setRascunho((atual) => ({ ...atual, fim }))}
						/>
					</div>

					{erro && (
						<p id={erroId} className="text-small text-danger">
							{erro}
						</p>
					)}

					<div className="flex flex-wrap items-center justify-between gap-2">
						<Button
							type="button"
							variant="ghost"
							size="sm"
							disabled={!padrao}
							onClick={() => {
								if (padrao) aplicar(padrao);
							}}
						>
							Últimos 12 meses
						</Button>
						<Button type="submit" size="sm">
							Aplicar
						</Button>
					</div>
				</form>
			</PopoverContent>
		</Popover>
	);
}
