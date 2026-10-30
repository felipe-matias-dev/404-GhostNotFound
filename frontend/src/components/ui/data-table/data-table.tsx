// Tabela de dados com a ordenação do Sortable Table do interior.dev
// (https://www.interior.dev/docs/sortable-table): as linhas viajam até a nova posição
// por transform, com mola e escalonamento, e a altura da tabela não muda ao reordenar.
// Lógica de ordenação original (estável, vazios no fim, 3º clique volta à ordem da API);
// adaptações para o portal VE-360:
// - tokens da marca, textos em português e collator pt-BR;
// - paginação no cliente (as rotas devolvem a lista inteira, ver DEC das OIs);
// - seleção múltipla controlada (`selected` + `onSelectedChange`), por página no cabeçalho;
// - linha clicável (`onRowClick`) com botão esticado na primeira coluna, acessível por teclado;
// - estados de carregando (molde das linhas), erro (com "Tentar de novo") e vazio;
// - abaixo de 48rem de largura do container (celular, painel estreito), vira lista de cards
//   com a ordenação em chips; os cards também viajam (layout animation).
import {
	ArrowsClockwiseIcon,
	ArrowsDownUpIcon,
	ArrowUpIcon,
	CaretLeftIcon,
	CaretRightIcon,
	TrayIcon,
	XCircleIcon,
} from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
	type ReactNode,
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";
import { Button } from "#/components/ui/button";
import { Checkbox } from "#/components/ui/checkbox";
import { cn } from "#/lib/utils";

const CELL = {
	type: "spring",
	stiffness: 520,
	damping: 34,
	mass: 0.45,
} as const;
const SMALL = {
	type: "spring",
	stiffness: 700,
	damping: 46,
	mass: 0.5,
} as const;
const EASE = [0.23, 1, 0.32, 1] as const;
const LEAVE = [0.4, 0, 1, 1] as const;
const HIDE = { duration: 0.12, ease: LEAVE } as const;
const SHOW = { duration: 0.25, ease: EASE } as const;
const INSTANT = { duration: 0 } as const;

const STEP = 0.018;
const STEP_CAP = 8;
const SETTLE_MS = 380;
const SKELETON_WIDTHS = [72, 56, 64, 48, 60] as const;

export type SortDirection = "asc" | "desc";

export type SortState = { columnId: string; direction: SortDirection };

type SortValue = string | number | null | undefined;

export type DataTableColumn<T> = {
	id: string;
	header: string;
	/** Trilha do grid (ex.: `"120px"`); sem ela, divide o espaço com as outras. */
	width?: string;
	align?: "start" | "end";
	numeric?: boolean;
	/** Padrão: ordenável quando tem `value`. */
	sortable?: boolean;
	/** Valor usado para ordenar e, sem `cell`, para exibir. */
	value?: (row: T) => SortValue;
	cell?: (row: T) => ReactNode;
};

export type DataTableProps<T> = {
	/** Nome acessível da tabela. */
	label: string;
	columns: DataTableColumn<T>[];
	/** Linhas na ordem da API; `undefined` enquanto não chegaram. */
	rows: T[] | undefined;
	/**
	 * Identifica o conjunto de linhas (ex.: o filtro). Quando muda, a tabela volta para a
	 * primeira página; uma recarga do mesmo conjunto mantém a página.
	 */
	resetKey?: string;
	getRowId: (row: T) => string;
	/** Nome da linha para leitor de tela (seleção, abrir). Padrão: valor da 1ª coluna. */
	getRowLabel?: (row: T) => string;
	loading?: boolean;
	/** Mensagem de erro; com ela, a tabela mostra o estado de erro. */
	error?: string | null;
	onRetry?: () => void;
	emptyMessage?: string;
	/** Ordenação controlada; omita para a tabela cuidar dela. `null` = ordem da API. */
	sort?: SortState | null;
	defaultSort?: SortState | null;
	onSortChange?: (next: SortState | null) => void;
	/** A API já devolve as linhas ordenadas; mantém apenas os controles visuais. */
	serverSort?: boolean;
	pageSize?: number;
	/** Paginação controlada pela API, com índice de página começando em zero. */
	pagination?: {
		page: number;
		total: number;
		onPageChange: (page: number) => void;
		disabled?: boolean;
	};
	rowHeight?: number;
	/** Seleção múltipla: ativa quando `onSelectedChange` é passado. */
	selected?: ReadonlySet<string>;
	onSelectedChange?: (next: Set<string>) => void;
	isRowSelectable?: (row: T) => boolean;
	onRowClick?: (row: T) => void;
	/**
	 * Ações da linha (botões). Na tabela, última coluna; no card, rodapé. Não disparam
	 * `onRowClick`.
	 */
	rowActions?: (row: T) => ReactNode;
	/** Trilha do grid da coluna de ações (ex.: `"200px"`). Padrão: `"160px"`. */
	rowActionsWidth?: string;
	/**
	 * Linha sob o ponteiro ou com foco do teclado (`null` ao sair), para destacar o mesmo
	 * item em outro lugar da tela (ex.: a região no mapa).
	 */
	onRowHover?: (row: T | null) => void;
	/** Largura do container abaixo da qual a tabela vira lista de cards. Padrão: 48rem. */
	cardsBelow?: CardsBreakpoint;
	className?: string;
};

// Classes estáticas para o Tailwind gerar: tabela a partir do ponto, cards abaixo dele.
const BREAKPOINTS = {
	"3xl": { table: "@3xl:block", cards: "@3xl:hidden" },
	"4xl": { table: "@4xl:block", cards: "@4xl:hidden" },
	"5xl": { table: "@5xl:block", cards: "@5xl:hidden" },
} as const;

export type CardsBreakpoint = keyof typeof BREAKPOINTS;

function isEmpty(value: SortValue) {
	return value === null || value === undefined || value === "";
}

const collator = new Intl.Collator("pt-BR", {
	numeric: true,
	sensitivity: "base",
});

function useSortableRows<T>({
	rows,
	getRowId,
	getValue,
	sort,
	defaultSort,
	onSortChange,
	serverSort,
}: {
	rows: T[];
	getRowId: (row: T) => string;
	getValue: (row: T, columnId: string) => SortValue;
	sort: SortState | null | undefined;
	defaultSort: SortState | null;
	onSortChange?: (next: SortState | null) => void;
	serverSort: boolean;
}) {
	const [internal, setInternal] = useState<SortState | null>(defaultSort);
	const controlled = sort !== undefined;
	const current = controlled ? sort : internal;

	const ordered = useMemo(() => {
		const base = rows.map((row, i) => ({ id: getRowId(row), row, i }));
		if (current && !serverSort) {
			const dir = current.direction === "asc" ? 1 : -1;
			base.sort((x, y) => {
				const a = getValue(x.row, current.columnId);
				const b = getValue(y.row, current.columnId);
				const emptyA = isEmpty(a);
				const emptyB = isEmpty(b);
				if (emptyA || emptyB) {
					if (emptyA && emptyB) return x.i - y.i;
					return emptyA ? 1 : -1;
				}
				const d =
					typeof a === "number" && typeof b === "number"
						? a - b
						: collator.compare(String(a), String(b));
				return d === 0 ? x.i - y.i : d * dir;
			});
		}
		return base.map(({ id, row }) => ({ id, row }));
	}, [rows, current, getRowId, getValue, serverSort]);

	const toggle = (columnId: string) => {
		const next: SortState | null =
			!current || current.columnId !== columnId
				? { columnId, direction: "asc" }
				: current.direction === "asc"
					? { columnId, direction: "desc" }
					: null;
		if (!controlled) setInternal(next);
		onSortChange?.(next);
	};

	const ariaSort = (columnId: string): "ascending" | "descending" | "none" =>
		current?.columnId === columnId
			? current.direction === "asc"
				? "ascending"
				: "descending"
			: "none";

	return { sort: current, ordered, toggle, ariaSort };
}

function SortArrow({
	state,
	reduced,
}: {
	state: "ascending" | "descending" | "none";
	reduced: boolean;
}) {
	const active = state !== "none";
	const transition = reduced ? INSTANT : SMALL;
	// Fechada (largura 0) quando a coluna não ordena: o cabeçalho ganha o espaço da seta.
	return (
		<motion.span
			aria-hidden
			className="flex shrink-0 justify-center overflow-hidden"
			initial={false}
			animate={{ width: active ? 12 : 0 }}
			transition={transition}
		>
			<motion.span
				className="flex text-text"
				initial={false}
				animate={{
					rotate: state === "descending" ? 180 : 0,
					opacity: active ? 1 : 0,
					scale: active ? 1 : 0.72,
				}}
				transition={transition}
			>
				<ArrowUpIcon weight="bold" className="size-3" />
			</motion.span>
		</motion.span>
	);
}

function StateBlock({
	tone,
	children,
	action,
}: {
	tone: "error" | "empty";
	children: ReactNode;
	action?: ReactNode;
}) {
	const Icon = tone === "error" ? XCircleIcon : TrayIcon;
	return (
		<div className="flex min-h-40 flex-col items-center justify-center gap-3 px-4 py-8 text-center">
			<Icon
				aria-hidden
				className={cn(
					"size-6",
					tone === "error" ? "text-danger" : "text-text-muted",
				)}
			/>
			<p
				className={cn(
					"max-w-prose text-body",
					tone === "error" ? "text-text" : "text-text-muted",
				)}
			>
				{children}
			</p>
			{action}
		</div>
	);
}

export function DataTable<T>({
	label,
	columns,
	rows,
	resetKey,
	getRowId,
	getRowLabel,
	loading = false,
	error = null,
	onRetry,
	emptyMessage = "Nenhum registro encontrado.",
	sort,
	defaultSort = null,
	onSortChange,
	serverSort = false,
	pageSize = 10,
	pagination,
	rowHeight = 44,
	selected,
	onSelectedChange,
	isRowSelectable,
	onRowClick,
	rowActions,
	rowActionsWidth = "160px",
	onRowHover,
	cardsBelow = "3xl",
	className,
}: DataTableProps<T>) {
	const reduced = useReducedMotion() ?? false;
	const [page, setPage] = useState(0);
	const [touched, setTouched] = useState(false);
	const [moving, setMoving] = useState(false);
	const settleTimer = useRef<number | undefined>(undefined);

	useEffect(() => () => window.clearTimeout(settleTimer.current), []);

	const data = useMemo(() => rows ?? [], [rows]);

	// Outro conjunto de linhas (outro filtro): volta para a primeira página.
	const [previousResetKey, setPreviousResetKey] = useState(resetKey);
	if (resetKey !== previousResetKey) {
		setPreviousResetKey(resetKey);
		setPage(0);
	}

	const getValue = useCallback(
		(row: T, columnId: string) =>
			columns.find((c) => c.id === columnId)?.value?.(row) ?? null,
		[columns],
	);

	const {
		sort: current,
		ordered,
		toggle,
		ariaSort,
	} = useSortableRows({
		rows: data,
		getRowId,
		getValue,
		sort,
		defaultSort,
		onSortChange,
		serverSort,
	});

	const selectable = onSelectedChange !== undefined;
	const chosen = selected ?? new Set<string>();

	const total = pagination?.total ?? ordered.length;
	const pageCount = Math.max(1, Math.ceil(total / pageSize));
	const pageIndex = pagination
		? pagination.page
		: Math.min(page, pageCount - 1);
	const start = pageIndex * pageSize;
	const pageRows = pagination
		? ordered
		: ordered.slice(start, start + pageSize);
	const selectableRows = pageRows.filter(
		({ row }) => isRowSelectable?.(row) ?? true,
	);
	const chosenOnPage = selectableRows.filter(({ id }) => chosen.has(id)).length;
	const allOnPage =
		selectableRows.length > 0 && chosenOnPage === selectableRows.length;
	const someOnPage = chosenOnPage > 0 && !allOnPage;

	const template = [
		...(selectable ? ["16px"] : []),
		...columns.map((c) => c.width ?? "minmax(0, 1fr)"),
		...(rowActions ? [rowActionsWidth] : []),
	].join(" ");

	const isSortable = (column: DataTableColumn<T>) =>
		column.sortable ?? column.value !== undefined;

	const nameOf = (row: T) =>
		getRowLabel?.(row) ?? String(columns[0]?.value?.(row) ?? getRowId(row));

	const onToggle = (columnId: string) => {
		setTouched(true);
		toggle(columnId);
		setPage(0);
		if (reduced) return;
		setMoving(true);
		window.clearTimeout(settleTimer.current);
		settleTimer.current = window.setTimeout(() => setMoving(false), SETTLE_MS);
	};

	const setRowSelected = (id: string, on: boolean) => {
		const next = new Set(chosen);
		if (on) next.add(id);
		else next.delete(id);
		onSelectedChange?.(next);
	};

	const setPageSelected = (on: boolean) => {
		const next = new Set(chosen);
		for (const { id } of selectableRows) {
			if (on) next.add(id);
			else next.delete(id);
		}
		onSelectedChange?.(next);
	};

	const renderCell = (column: DataTableColumn<T>, row: T) => {
		if (column.cell) return column.cell(row);
		const raw = column.value?.(row);
		return isEmpty(raw) ? "—" : String(raw);
	};

	const openButton = (row: T, content: ReactNode, className?: string) =>
		onRowClick ? (
			<button
				type="button"
				onClick={() => onRowClick(row)}
				aria-label={`Abrir ${nameOf(row)}`}
				className={cn(
					"min-w-0 cursor-pointer truncate text-left outline-none after:absolute after:inset-0 after:content-[''] focus-visible:after:shadow-[inset_0_0_0_2px_var(--color-focus-ring)] focus-visible:shadow-none",
					className,
				)}
			>
				{content}
			</button>
		) : (
			content
		);

	const activeHeader = columns.find((c) => c.id === current?.columnId)?.header;
	const message = !touched
		? ""
		: current && activeHeader
			? `Ordenado por ${activeHeader}, ${
					current.direction === "asc" ? "crescente" : "decrescente"
				}. ${data.length} linhas.`
			: `Ordem original restaurada. ${data.length} linhas.`;

	const showError = Boolean(error);
	const showSkeleton = !showError && loading && rows === undefined;
	const showEmpty = !showError && !showSkeleton && data.length === 0;
	const showRows = !showError && !showSkeleton && !showEmpty;
	const busy = loading && rows !== undefined;

	const stateBody = showError ? (
		<StateBlock
			tone="error"
			action={
				onRetry ? (
					<Button variant="outline" size="sm" onClick={onRetry}>
						<ArrowsClockwiseIcon aria-hidden />
						Tentar de novo
					</Button>
				) : undefined
			}
		>
			{error}
		</StateBlock>
	) : showEmpty ? (
		<StateBlock tone="empty">{emptyMessage}</StateBlock>
	) : null;

	const skeletonCount = Math.min(pageSize, 5);

	return (
		<div
			className={cn("@container flex flex-col gap-2", className)}
			aria-busy={loading}
		>
			{/* Tabela: container a partir de `cardsBelow`. */}
			<div
				className={cn(
					"relative hidden overflow-hidden rounded-lg border border-border bg-surface-1",
					BREAKPOINTS[cardsBelow].table,
				)}
			>
				<table
					aria-label={label}
					aria-rowcount={total + 1}
					aria-colcount={
						columns.length + (selectable ? 1 : 0) + (rowActions ? 1 : 0)
					}
					className="block w-full"
				>
					<thead className="block">
						<tr
							aria-rowindex={1}
							className="grid h-10 items-center gap-x-2 border-b border-border px-3"
							style={{ gridTemplateColumns: template }}
						>
							{selectable && (
								<th scope="col" className="flex min-w-0">
									<Checkbox
										checked={allOnPage}
										indeterminate={someOnPage}
										onChange={setPageSelected}
										label="Selecionar todas desta página"
										disabled={selectableRows.length === 0}
									/>
								</th>
							)}
							{columns.map((column) => {
								const state = ariaSort(column.id);
								const end = column.align === "end";
								const headerText = cn(
									"truncate text-small uppercase tracking-[0.04em]",
									state !== "none"
										? "text-text"
										: "text-text-muted group-hover:text-text",
								);
								return (
									<th
										key={column.id}
										scope="col"
										aria-sort={isSortable(column) ? state : undefined}
										className="min-w-0 font-normal"
									>
										{isSortable(column) ? (
											<button
												type="button"
												onClick={() => onToggle(column.id)}
												className={cn(
													"group flex h-7 w-full cursor-pointer items-center gap-1.5 rounded-md px-1.5 outline-none focus-visible:bg-hover focus-visible:shadow-[inset_0_0_0_1px_var(--color-focus-ring)]",
													end && "flex-row-reverse",
												)}
											>
												<span className={headerText}>{column.header}</span>
												<SortArrow state={state} reduced={reduced} />
											</button>
										) : (
											<span
												className={cn(
													"block px-1.5",
													headerText,
													end && "text-right",
												)}
											>
												{column.header}
											</span>
										)}
									</th>
								);
							})}
							{rowActions && (
								<th scope="col" className="min-w-0 font-normal">
									<span className="block truncate px-1.5 text-small text-text-muted uppercase tracking-[0.04em]">
										Ações
									</span>
								</th>
							)}
						</tr>
					</thead>

					{stateBody && (
						<tbody className="block">
							<tr className="block">
								<td className="block">{stateBody}</td>
							</tr>
						</tbody>
					)}

					{showSkeleton && (
						<tbody aria-hidden className="block">
							{Array.from({ length: skeletonCount }, (_, i) => (
								<motion.tr
									// biome-ignore lint/suspicious/noArrayIndexKey: linhas fixas do molde.
									key={i}
									className="grid items-center gap-x-2 border-b border-border px-3 last:border-b-0"
									style={{ height: rowHeight, gridTemplateColumns: template }}
									initial={{ opacity: 0 }}
									animate={{ opacity: 1 }}
									transition={
										reduced ? INSTANT : { ...SHOW, delay: 0.12 + i * STEP }
									}
								>
									{selectable && (
										<td className="size-4 rounded-sm bg-pressed" />
									)}
									{columns.map((column, c) => (
										<td
											key={column.id}
											className={cn(
												"flex px-1.5",
												column.align === "end" && "justify-end",
											)}
										>
											<div
												className="h-2 rounded-sm bg-pressed"
												style={{
													width: `${SKELETON_WIDTHS[(i + c) % SKELETON_WIDTHS.length]}%`,
												}}
											/>
										</td>
									))}
									{rowActions && (
										<td className="flex px-1.5">
											<div
												className="h-2 rounded-sm bg-pressed"
												style={{ width: "60%" }}
											/>
										</td>
									)}
								</motion.tr>
							))}
						</tbody>
					)}

					{showRows && (
						<tbody
							className="relative block"
							style={{ height: pageRows.length * rowHeight }}
						>
							<AnimatePresence initial={false}>
								{pageRows.map(({ id, row }, index) => {
									const isSelected = selectable && chosen.has(id);
									const y = index * rowHeight;
									return (
										<motion.tr
											key={id}
											aria-rowindex={start + index + 2}
											onPointerEnter={() => onRowHover?.(row)}
											onPointerLeave={() => onRowHover?.(null)}
											onFocus={() => onRowHover?.(row)}
											onBlur={() => onRowHover?.(null)}
											aria-selected={selectable ? isSelected : undefined}
											initial={{ opacity: 0, y }}
											animate={{ opacity: 1, y }}
											exit={{
												opacity: 0,
												transition: reduced ? INSTANT : HIDE,
											}}
											transition={
												reduced
													? INSTANT
													: {
															...CELL,
															delay: Math.min(index, STEP_CAP) * STEP,
														}
											}
											className={cn(
												"absolute inset-x-0 top-0 grid items-center gap-x-2 px-3 transition-colors duration-150 before:absolute before:inset-y-0 before:left-0 before:w-0.5",
												isSelected
													? "bg-accent-subtle before:bg-accent"
													: "hover:bg-hover",
											)}
											style={{
												height: rowHeight,
												gridTemplateColumns: template,
											}}
										>
											{selectable && (
												<td className="flex min-w-0">
													<Checkbox
														checked={isSelected}
														onChange={(on) => setRowSelected(id, on)}
														label={`Selecionar ${nameOf(row)}`}
														disabled={!(isRowSelectable?.(row) ?? true)}
													/>
												</td>
											)}
											{columns.map((column, c) => {
												const content = renderCell(column, row);
												return (
													<td
														key={column.id}
														className={cn(
															"flex min-w-0 px-1.5 text-body",
															column.align === "end" &&
																"justify-end text-right",
															column.numeric && "tabular-nums",
															c === 0
																? "font-medium text-text"
																: "text-text-muted",
														)}
													>
														{c === 0 ? (
															openButton(row, content)
														) : (
															<span className="min-w-0 truncate">
																{content}
															</span>
														)}
													</td>
												);
											})}
											{rowActions && (
												<td className="relative z-10 flex min-w-0 items-center px-1.5">
													{rowActions(row)}
												</td>
											)}
										</motion.tr>
									);
								})}
							</AnimatePresence>
						</tbody>
					)}
				</table>

				{showRows && (
					<motion.div
						aria-hidden
						initial={false}
						animate={{ opacity: moving ? 0 : 1 }}
						transition={moving ? HIDE : SHOW}
						className="pointer-events-none absolute inset-x-0 top-10 bottom-0"
					>
						{Array.from(
							{ length: Math.max(0, pageRows.length - 1) },
							(_, i) => (
								<div
									// biome-ignore lint/suspicious/noArrayIndexKey: divisórias por posição, não por linha.
									key={i}
									className="absolute inset-x-0 border-t border-border"
									style={{ top: (i + 1) * rowHeight }}
								/>
							),
						)}
					</motion.div>
				)}
			</div>

			{/* Lista de cards: container abaixo de `cardsBelow`. */}
			<div className={cn("flex flex-col gap-2", BREAKPOINTS[cardsBelow].cards)}>
				{showRows && (
					<div className="flex items-center gap-2">
						{selectable && (
							<Checkbox
								checked={allOnPage}
								indeterminate={someOnPage}
								onChange={setPageSelected}
								label="Selecionar todas desta página"
								disabled={selectableRows.length === 0}
								className="ml-3"
							/>
						)}
						{columns.some(isSortable) && (
							<>
								<ArrowsDownUpIcon
									aria-hidden
									className={cn(
										"size-4 shrink-0 text-text-muted",
										!selectable && "ml-1",
									)}
								/>
								{/* biome-ignore lint/a11y/useSemanticElements: grupo de botões, não formulário. */}
								<div
									role="group"
									aria-label="Ordenar por"
									className="-my-1 flex min-w-0 flex-1 gap-1.5 overflow-x-auto py-1 pr-1"
								>
									{columns.filter(isSortable).map((column) => {
										const state = ariaSort(column.id);
										return (
											<button
												key={column.id}
												type="button"
												aria-pressed={state !== "none"}
												aria-label={`Ordenar por ${column.header}${
													state === "none"
														? ""
														: state === "ascending"
															? ", crescente"
															: ", decrescente"
												}`}
												onClick={() => onToggle(column.id)}
												className={cn(
													"flex h-7 shrink-0 cursor-pointer items-center gap-1 rounded-full border px-2.5 text-small outline-none transition-colors duration-150 focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50",
													state !== "none"
														? "border-border-strong bg-surface-2 text-text"
														: "border-border text-text-muted hover:bg-hover hover:text-text",
												)}
											>
												{column.header}
												<SortArrow state={state} reduced={reduced} />
											</button>
										);
									})}
								</div>
							</>
						)}
					</div>
				)}

				{stateBody && (
					<div className="rounded-lg border border-border bg-surface-1">
						{stateBody}
					</div>
				)}

				{showSkeleton && (
					<div aria-hidden className="flex flex-col gap-2">
						{Array.from({ length: Math.min(skeletonCount, 3) }, (_, i) => (
							<motion.div
								// biome-ignore lint/suspicious/noArrayIndexKey: cards fixos do molde.
								key={i}
								className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-3"
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
								transition={
									reduced ? INSTANT : { ...SHOW, delay: 0.12 + i * STEP }
								}
							>
								<div className="h-2.5 w-2/5 rounded-sm bg-pressed" />
								<div className="grid grid-cols-2 gap-x-3 gap-y-2">
									{columns.slice(1).map((column) => (
										<div
											key={column.id}
											className="h-2 w-3/5 rounded-sm bg-pressed"
										/>
									))}
								</div>
							</motion.div>
						))}
					</div>
				)}

				{showRows && (
					<ul aria-label={label} className="flex flex-col gap-2">
						<AnimatePresence initial={false} mode="popLayout">
							{pageRows.map(({ id, row }, index) => {
								const isSelected = selectable && chosen.has(id);
								const [first, ...rest] = columns;
								return (
									<motion.li
										key={id}
										layout={reduced ? false : "position"}
										onPointerEnter={() => onRowHover?.(row)}
										onPointerLeave={() => onRowHover?.(null)}
										onFocus={() => onRowHover?.(row)}
										onBlur={() => onRowHover?.(null)}
										aria-selected={selectable ? isSelected : undefined}
										initial={{ opacity: 0, scale: 0.98 }}
										animate={{ opacity: 1, scale: 1 }}
										exit={{
											opacity: 0,
											scale: 0.98,
											transition: reduced ? INSTANT : HIDE,
										}}
										transition={
											reduced
												? INSTANT
												: { ...CELL, delay: Math.min(index, STEP_CAP) * STEP }
										}
										className={cn(
											"relative overflow-hidden rounded-lg border p-3 transition-colors duration-150 before:absolute before:inset-y-0 before:left-0 before:w-0.5",
											isSelected
												? "border-border-strong bg-accent-subtle before:bg-accent"
												: "border-border bg-surface-1",
											onRowClick && !isSelected && "hover:bg-hover",
										)}
									>
										<div className="flex items-center gap-2.5">
											{selectable && (
												<Checkbox
													checked={isSelected}
													onChange={(on) => setRowSelected(id, on)}
													label={`Selecionar ${nameOf(row)}`}
													disabled={!(isRowSelectable?.(row) ?? true)}
												/>
											)}
											{first && (
												<span className="flex min-w-0 flex-1 text-body font-medium text-text">
													{openButton(row, renderCell(first, row), "flex-1")}
												</span>
											)}
											{onRowClick && (
												<CaretRightIcon
													aria-hidden
													className="size-4 shrink-0 text-text-muted"
												/>
											)}
										</div>
										{rest.length > 0 && (
											<dl className="mt-2.5 grid grid-cols-2 gap-x-3 gap-y-2">
												{rest.map((column) => (
													<div key={column.id} className="min-w-0">
														<dt className="truncate text-small text-text-muted">
															{column.header}
														</dt>
														<dd
															className={cn(
																"truncate text-body text-text",
																column.numeric && "tabular-nums",
															)}
														>
															{renderCell(column, row)}
														</dd>
													</div>
												))}
											</dl>
										)}
										{rowActions && (
											<div className="relative z-10 mt-2.5 flex flex-wrap items-center gap-1">
												{rowActions(row)}
											</div>
										)}
									</motion.li>
								);
							})}
						</AnimatePresence>
					</ul>
				)}
			</div>

			{(showRows || (showEmpty && pagination && pageIndex > 0)) && (
				<div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-1">
					<p
						className={cn(
							"text-small tabular-nums text-text-muted",
							busy && "text-text-disabled",
						)}
					>
						{showRows
							? `${start + 1}–${start + pageRows.length} de ${total}`
							: `Nenhuma linha nesta página · ${total} no total`}
						{selectable && chosen.size > 0 && (
							<>
								{" · "}
								<span className="text-text">
									{chosen.size}{" "}
									{chosen.size === 1 ? "selecionada" : "selecionadas"}
								</span>{" "}
								<button
									type="button"
									onClick={() => onSelectedChange?.(new Set())}
									className="cursor-pointer rounded-sm text-info underline-offset-4 outline-none hover:underline focus-visible:underline"
								>
									Limpar
								</button>
							</>
						)}
					</p>
					{(pageCount > 1 || pageIndex > 0) && (
						<nav
							aria-label={`Páginas de ${label}`}
							className="flex items-center gap-1"
						>
							<Button
								variant="ghost"
								size="icon-sm"
								aria-label="Página anterior"
								disabled={pageIndex === 0 || pagination?.disabled}
								onClick={() =>
									pagination
										? pagination.onPageChange(pageIndex - 1)
										: setPage(pageIndex - 1)
								}
							>
								<CaretLeftIcon aria-hidden />
							</Button>
							<span className="min-w-16 text-center text-small tabular-nums text-text-muted">
								{pageIndex + 1} de {pageCount}
							</span>
							<Button
								variant="ghost"
								size="icon-sm"
								aria-label="Próxima página"
								disabled={pageIndex >= pageCount - 1 || pagination?.disabled}
								onClick={() =>
									pagination
										? pagination.onPageChange(pageIndex + 1)
										: setPage(pageIndex + 1)
								}
							>
								<CaretRightIcon aria-hidden />
							</Button>
						</nav>
					)}
				</div>
			)}

			<output aria-live="polite" className="sr-only">
				{message}
			</output>
		</div>
	);
}
