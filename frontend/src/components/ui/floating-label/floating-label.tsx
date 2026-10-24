// Floating Label do interior.dev (https://www.interior.dev/docs/floating-label), o mesmo
// arquivo que `npx shadcn@latest add https://www.interior.dev/r/floating-label.json` instala.
// A lógica do hook é a original (o rótulo nunca vira placeholder: sobe para um espaço
// reservado acima do texto, em mola; campo já preenchido não anima ao carregar; contador com a
// largura do maior valor possível). Adaptações para o portal VE-360:
// - tokens da marca: campo surface-1 + border-strong, foco igual ao do Button (borda + anel
//   `focus-ring`), inválido em `danger`, desabilitado sem opacidade;
// - tipografia `text-body` no campo e `text-small` no rótulo erguido, na dica e no contador;
// - `FloatingLabelTextarea`, que não existe no original (só uma linha): o mesmo hook, com o
//   rótulo em repouso na primeira linha do texto.
import { motion, useReducedMotion } from "motion/react";
import {
	type ChangeEvent,
	type ComponentProps,
	type ReactNode,
	type Ref,
	type RefObject,
	useCallback,
	useEffect,
	useId,
	useLayoutEffect,
	useRef,
	useState,
} from "react";
import { cn } from "#/lib/utils";

const INSTANT = { duration: 0 } as const;
const LIFT = {
	type: "spring",
	stiffness: 760,
	damping: 46,
	mass: 0.5,
} as const;

// Espaço reservado acima do campo para o rótulo erguido (px), e quanto ele encolhe:
// de `text-body` (14px) para o tamanho de `text-small` (12px).
const SLOT = 20;
const SLIDE = -12;
const SHRINK = 12 / 14;
// Topo do rótulo em repouso (px a partir do topo do bloco): centro do input de 40px, ou a
// primeira linha do textarea (borda de 1px + 10px de respiro).
const REPOUSO = { input: SLOT + 10, textarea: SLOT + 11 } as const;

const useIsomorphicLayoutEffect =
	typeof window === "undefined" ? useEffect : useLayoutEffect;

type Campo = HTMLInputElement | HTMLTextAreaElement;

export type UseFloatingLabelOptions = {
	value?: string;
	defaultValue?: string;
	disabled?: boolean;
};

export type UseFloatingLabelReturn<E extends Campo> = {
	ref: RefObject<E | null>;
	raised: boolean;
	focused: boolean;
	filled: boolean;
	length: number;
	instant: boolean;
	fieldProps: {
		onFocus: () => void;
		onBlur: () => void;
		onChange: (event: ChangeEvent<E>) => void;
	};
};

type Fill = { length: number; instant: boolean };

export function useFloatingLabel<E extends Campo = HTMLInputElement>({
	value,
	defaultValue,
	disabled = false,
}: UseFloatingLabelOptions = {}): UseFloatingLabelReturn<E> {
	const ref = useRef<E | null>(null);
	const mounted = useRef(false);

	const [focused, setFocused] = useState(false);
	const [fill, setFill] = useState<Fill>({
		length: (value ?? defaultValue ?? "").length,
		instant: true,
	});

	const settle = useCallback((next: number, instant: boolean) => {
		setFill((prev) =>
			prev.length === next && prev.instant === instant
				? prev
				: { length: next, instant },
		);
	}, []);

	useIsomorphicLayoutEffect(() => {
		const el = ref.current;
		const next = value !== undefined ? value.length : el ? el.value.length : 0;
		settle(next, !mounted.current);
		mounted.current = true;
	}, [value, settle]);

	useEffect(() => {
		setFill((prev) => (prev.instant ? { ...prev, instant: false } : prev));
	}, []);

	useEffect(() => {
		const el = ref.current;
		if (!el || value !== undefined) return;
		const read = () => settle(el.value.length, false);
		el.addEventListener("input", read);
		el.addEventListener("change", read);
		return () => {
			el.removeEventListener("input", read);
			el.removeEventListener("change", read);
		};
	}, [value, settle]);

	useEffect(() => {
		if (disabled) setFocused(false);
	}, [disabled]);

	const onFocus = useCallback(() => setFocused(true), []);
	const onBlur = useCallback(() => setFocused(false), []);
	const onChange = useCallback(
		(event: ChangeEvent<E>) => settle(event.currentTarget.value.length, false),
		[settle],
	);

	return {
		ref,
		raised: focused || fill.length > 0,
		focused,
		filled: fill.length > 0,
		length: fill.length,
		instant: fill.instant && !focused,
		fieldProps: { onFocus, onBlur, onChange },
	};
}

type BaseProps<E extends Campo> = {
	label: string;
	value?: string;
	defaultValue?: string;
	/** Recebe o valor primeiro: `onChange={setTexto}` já é o handler inteiro. */
	onChange?: (value: string, event: ChangeEvent<E>) => void;
	onFocus?: () => void;
	onBlur?: () => void;
	/** Linha abaixo do campo, lida uma vez pelo leitor de tela (aria-describedby). */
	hint?: string;
	/** Pinta borda e rótulo de `danger` e marca `aria-invalid`; a mensagem vem no `hint`. */
	invalid?: boolean;
	id?: string;
	name?: string;
	/** Liga o contador, com a largura reservada para o maior valor. */
	maxLength?: number;
	required?: boolean;
	disabled?: boolean;
	readOnly?: boolean;
	inputRef?: Ref<E>;
	className?: string;
};

function useCampo<E extends Campo>(props: BaseProps<E>) {
	const auto = useId();
	const fieldId = props.id ?? `${auto}-campo`;
	const hintId = `${auto}-dica`;
	const reduced = useReducedMotion();
	const estado = useFloatingLabel<E>({
		value: props.value,
		defaultValue: props.defaultValue,
		disabled: props.disabled,
	});
	const { ref } = estado;
	const { inputRef } = props;

	const attach = useCallback(
		(node: E | null) => {
			ref.current = node;
			if (typeof inputRef === "function") inputRef(node);
			else if (inputRef) inputRef.current = node;
		},
		[ref, inputRef],
	);

	const controle = {
		ref: attach,
		id: fieldId,
		name: props.name,
		value: props.value,
		defaultValue: props.defaultValue,
		maxLength: props.maxLength,
		required: props.required,
		disabled: props.disabled,
		readOnly: props.readOnly,
		"aria-required": props.required || undefined,
		"aria-invalid": props.invalid || undefined,
		"aria-describedby": props.hint ? hintId : undefined,
		onFocus: () => {
			estado.fieldProps.onFocus();
			props.onFocus?.();
		},
		onBlur: () => {
			estado.fieldProps.onBlur();
			props.onBlur?.();
		},
		onChange: (event: ChangeEvent<E>) => {
			estado.fieldProps.onChange(event);
			props.onChange?.(event.currentTarget.value, event);
		},
	};

	return {
		...estado,
		fieldId,
		hintId,
		move: reduced || estado.instant ? INSTANT : LIFT,
		controle,
	};
}

/** O que a moldura mostra do estado do campo (rótulo, foco, contador). */
type EstadoMoldura = {
	raised: boolean;
	focused: boolean;
	length: number;
	move: typeof INSTANT | typeof LIFT;
	fieldId: string;
	hintId: string;
};

type AparenciaMoldura = Pick<
	BaseProps<Campo>,
	| "label"
	| "hint"
	| "invalid"
	| "maxLength"
	| "required"
	| "disabled"
	| "className"
>;

function Moldura({
	tipo,
	campo,
	props,
	children,
}: {
	tipo: keyof typeof REPOUSO;
	campo: EstadoMoldura;
	props: AparenciaMoldura;
	children: ReactNode;
}) {
	const { label, hint, invalid = false, maxLength, required, disabled } = props;
	const { raised, focused, length, move, fieldId, hintId } = campo;
	const repouso = REPOUSO[tipo];

	return (
		<div className={cn("w-full", props.className)}>
			<div className="relative" style={{ paddingTop: SLOT }}>
				<div
					className={cn(
						"relative rounded-md border bg-surface-1 transition-[border-color,box-shadow] duration-150 motion-reduce:transition-none",
						invalid
							? "border-danger"
							: focused
								? "border-focus-ring ring-3 ring-focus-ring/50"
								: "border-border-strong",
						disabled && "border-border bg-surface-2",
					)}
				>
					{children}
				</div>
				<motion.label
					htmlFor={fieldId}
					initial={false}
					animate={{
						y: raised ? -repouso : 0,
						x: raised ? SLIDE : 0,
						scale: raised ? SHRINK : 1,
					}}
					transition={move}
					style={{ originX: 0, originY: 0, top: repouso }}
					className={cn(
						"pointer-events-auto absolute left-3 block cursor-text text-body select-none",
						disabled
							? "text-text-disabled"
							: invalid
								? "text-danger"
								: raised
									? "text-text"
									: "text-text-muted",
					)}
				>
					{label}
					{required ? (
						<span aria-hidden className="ml-0.5 text-text-muted">
							*
						</span>
					) : null}
				</motion.label>
			</div>

			<div className="mt-1.5 flex min-h-4 items-start gap-3">
				<p
					aria-hidden
					className={cn(
						"min-w-0 flex-1 text-small",
						invalid ? "text-danger" : "text-text-muted",
					)}
				>
					{hint}
				</p>
				{maxLength !== undefined ? (
					<span
						aria-hidden
						className="grid shrink-0 justify-items-end font-mono text-small tabular-nums text-text-muted"
					>
						<span className="invisible col-start-1 row-start-1">
							{maxLength} / {maxLength}
						</span>
						<span className="col-start-1 row-start-1">
							{length} / {maxLength}
						</span>
					</span>
				) : null}
				{hint ? (
					<span id={hintId} className="sr-only">
						{hint}
					</span>
				) : null}
			</div>
		</div>
	);
}

const TEXTO =
	"w-full rounded-md bg-transparent px-3 text-body text-text outline-none disabled:cursor-not-allowed disabled:text-text-disabled";

export type FloatingLabelInputProps = BaseProps<HTMLInputElement> & {
	type?: "text" | "email" | "password" | "search" | "tel" | "url";
	autoComplete?: string;
	inputMode?: ComponentProps<"input">["inputMode"];
};

export function FloatingLabelInput(props: FloatingLabelInputProps) {
	const campo = useCampo<HTMLInputElement>(props);
	return (
		<Moldura tipo="input" campo={campo} props={props}>
			<input
				{...campo.controle}
				type={props.type ?? "text"}
				autoComplete={props.autoComplete}
				inputMode={props.inputMode}
				className={cn(TEXTO, "block h-10")}
			/>
		</Moldura>
	);
}

export type FloatingLabelTextareaProps = BaseProps<HTMLTextAreaElement> & {
	rows?: number;
};

export function FloatingLabelTextarea(props: FloatingLabelTextareaProps) {
	const campo = useCampo<HTMLTextAreaElement>(props);
	return (
		<Moldura tipo="textarea" campo={campo} props={props}>
			<textarea
				{...campo.controle}
				rows={props.rows ?? 4}
				className={cn(TEXTO, "block resize-y py-2.5")}
			/>
		</Moldura>
	);
}
