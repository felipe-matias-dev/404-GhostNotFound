import { CaretDownIcon } from "@phosphor-icons/react";
import { HeaderTrilha } from "#/components/layout/header";
import {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbList,
	BreadcrumbSeparator,
} from "#/components/ui/breadcrumb";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuLabel,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "#/components/ui/dropdown-menu";
import { useDecomposicao } from "../hooks/use-decomposicao";
import type { ParPeriodos, Recorte } from "../types";

const TODOS = "";

function NivelMenu({
	nivel,
	todos,
	valor,
	opcoes,
	carregando,
	atual,
	onEscolher,
}: {
	nivel: string;
	todos: string;
	valor: string | undefined;
	opcoes: string[];
	carregando: boolean;
	/** Último nível da trilha: é o recorte que a página mostra. */
	atual: boolean;
	onEscolher: (valor: string | undefined) => void;
}) {
	const rotulo = valor ?? todos;
	return (
		<DropdownMenu>
			<DropdownMenuTrigger
				aria-label={`${nivel}: ${rotulo}. Trocar`}
				className="flex h-7 min-w-0 cursor-pointer items-center gap-1 rounded-md px-1.5 font-medium text-text outline-none transition-colors hover:bg-hover focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover"
			>
				<span className="truncate" aria-current={atual ? "page" : undefined}>
					{rotulo}
				</span>
				<CaretDownIcon
					aria-hidden
					className="size-3 shrink-0 text-text-muted"
				/>
			</DropdownMenuTrigger>
			<DropdownMenuContent>
				<DropdownMenuRadioGroup
					value={valor ?? TODOS}
					onValueChange={(next: string) => onEscolher(next || undefined)}
				>
					<DropdownMenuRadioItem value={TODOS}>{todos}</DropdownMenuRadioItem>
					<DropdownMenuSeparator />
					<DropdownMenuGroup>
						<DropdownMenuLabel>
							{carregando ? "Carregando…" : nivel}
						</DropdownMenuLabel>
						{opcoes.map((opcao) => (
							<DropdownMenuRadioItem key={opcao} value={opcao}>
								{opcao}
							</DropdownMenuRadioItem>
						))}
					</DropdownMenuGroup>
				</DropdownMenuRadioGroup>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}

const ordenar = (nomes: string[]) =>
	[...new Set(nomes)].sort((a, b) => a.localeCompare(b, "pt-BR"));

export function RecorteTrilha({
	par,
	recorte,
	onChange,
}: {
	par: ParPeriodos | undefined;
	recorte: Recorte;
	onChange: (proximo: Recorte) => void;
}) {
	const municipios = useDecomposicao(par, {});
	const bairros = useDecomposicao(
		par,
		{ municipio: recorte.municipio },
		Boolean(recorte.municipio),
	);

	return (
		<HeaderTrilha>
			<Breadcrumb aria-label="Recorte" className="min-w-0">
				<BreadcrumbList className="gap-0.5">
					<BreadcrumbSeparator className="mx-0.5" />
					<BreadcrumbItem>
						<NivelMenu
							nivel="Municípios"
							todos="Todos os municípios"
							valor={recorte.municipio}
							opcoes={ordenar(municipios.data?.map((l) => l.segmento) ?? [])}
							carregando={municipios.isPending}
							atual={!recorte.municipio}
							onEscolher={(municipio) => onChange({ municipio })}
						/>
					</BreadcrumbItem>
					{recorte.municipio && (
						<>
							<BreadcrumbSeparator className="mx-0.5" />
							<BreadcrumbItem>
								<NivelMenu
									nivel={`Bairros de ${recorte.municipio}`}
									todos="Todos os bairros"
									valor={recorte.bairro}
									opcoes={
										bairros.isPlaceholderData
											? []
											: ordenar(bairros.data?.map((l) => l.segmento) ?? [])
									}
									carregando={bairros.isPending || bairros.isPlaceholderData}
									atual
									onEscolher={(bairro) =>
										onChange({ municipio: recorte.municipio, bairro })
									}
								/>
							</BreadcrumbItem>
						</>
					)}
				</BreadcrumbList>
			</Breadcrumb>
		</HeaderTrilha>
	);
}
