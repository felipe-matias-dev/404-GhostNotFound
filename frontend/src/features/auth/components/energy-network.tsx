import { useEffect, useRef } from "react";

type Node = { x: number; z: number; kind: "station" | "uc" };
const NODES: Node[] = [
	{ x: -2.25, z: 2.8, kind: "station" },
	{ x: -1.75, z: 1.6, kind: "station" },
	{ x: -2.5, z: 0.95, kind: "uc" },
	{ x: -0.95, z: 0.85, kind: "uc" },
	{ x: 2.15, z: 2.7, kind: "station" },
	{ x: 1.65, z: 1.55, kind: "station" },
	{ x: 2.45, z: 0.9, kind: "uc" },
	{ x: 0.95, z: 0.82, kind: "uc" },
];
const EDGES = [
	[0, 1],
	[1, 2],
	[1, 3],
	[0, 4],
	[4, 5],
	[5, 6],
	[5, 7],
];

export function EnergyNetwork({ paused }: { paused: boolean }) {
	const canvasRef = useRef<HTMLCanvasElement>(null);
	const timeRef = useRef(0);

	useEffect(() => {
		const canvas = canvasRef.current;
		const host = canvas?.parentElement;
		const ctx = canvas?.getContext("2d");
		if (!canvas || !host || !ctx) return;
		const media = matchMedia("(prefers-reduced-motion: reduce)");
		let width = 0;
		let height = 0;
		let raf = 0;
		let last = 0;
		let time = timeRef.current;
		let previous = 0;
		const projected = new Float32Array(NODES.length * 2);
		const palette = getComputedStyle(host);
		const dot = palette.getPropertyValue("--color-text-muted").trim();
		const accent = palette.getPropertyValue("--color-accent-text").trim();
		const muted = palette.getPropertyValue("--color-text-muted").trim();

		function draw(t: number) {
			if (!ctx) return;
			ctx.clearRect(0, 0, width, height);
			const focal = width * 0.32;
			const horizon = height * 0.38;
			const half = (width / 2 / focal) * 3.8;
			const cols = Math.min(100, Math.ceil(width / 14));
			const rows = 46;
			ctx.fillStyle = dot;
			for (let row = 0; row < rows; row++) {
				const z = 3.8 * (0.38 / 3.8) ** (row / (rows - 1));
				const size = Math.min(2, 1.3 / z);
				ctx.globalAlpha = 0.08 + (row / rows) * 0.3;
				for (let col = 0; col < cols; col++) {
					const x = -half + (col / (cols - 1)) * half * 2;
					const wave =
						Math.sin(x * 2 + z * 2.4 - t * 0.35) * 0.075 +
						Math.sin(z * 4 + t * 0.22) * 0.035;
					const sx = width / 2 + (x / z) * focal;
					const sy = horizon + ((0.62 - wave) / z) * focal;
					if (sx < 0 || sx > width || sy > height) continue;
					ctx.fillRect(sx, sy, size, size);
				}
			}
			ctx.globalAlpha = 1;
			for (let i = 0; i < NODES.length; i++) {
				projected[i * 2] = width / 2 + (NODES[i].x / NODES[i].z) * focal;
				projected[i * 2 + 1] = horizon + (0.62 / NODES[i].z) * focal;
			}
			ctx.lineWidth = 1;
			for (let i = 0; i < EDGES.length; i++) {
				const [a, b] = EDGES[i];
				const ax = projected[a * 2];
				const ay = projected[a * 2 + 1];
				const bx = projected[b * 2];
				const by = projected[b * 2 + 1];
				const bend = (ay + by) / 2;
				ctx.strokeStyle = accent;
				ctx.globalAlpha = 0.24;
				ctx.beginPath();
				ctx.moveTo(ax, ay);
				ctx.lineTo(ax, bend);
				ctx.lineTo(bx, bend);
				ctx.lineTo(bx, by);
				ctx.stroke();
				const first = Math.abs(bend - ay);
				const across = Math.abs(bx - ax);
				const last = Math.abs(by - bend);
				const distance = ((t * 0.12 + i * 0.17) % 1) * (first + across + last);
				let px = ax;
				let py = ay;
				if (distance < first) py += Math.sign(bend - ay) * distance;
				else if (distance < first + across) {
					px += Math.sign(bx - ax) * (distance - first);
					py = bend;
				} else {
					px = bx;
					py = bend + Math.sign(by - bend) * (distance - first - across);
				}
				ctx.globalAlpha = 0.85;
				ctx.fillStyle = accent;
				ctx.fillRect(px - 2, py - 2, 4, 4);
			}
			for (let i = 0; i < NODES.length; i++) {
				const x = projected[i * 2];
				const y = projected[i * 2 + 1];
				const station = NODES[i].kind === "station";
				const size = station ? 10 : 7;
				ctx.globalAlpha = 0.65;
				ctx.strokeStyle = station ? accent : muted;
				ctx.beginPath();
				if (station) {
					ctx.moveTo(x, y - size);
					ctx.lineTo(x + size, y);
					ctx.lineTo(x, y + size);
					ctx.lineTo(x - size, y);
					ctx.closePath();
				} else {
					ctx.moveTo(x - size, y + size);
					ctx.lineTo(x - size, y - 2);
					ctx.lineTo(x, y - size);
					ctx.lineTo(x + size, y - 2);
					ctx.lineTo(x + size, y + size);
					ctx.closePath();
				}
				ctx.stroke();
				ctx.fillStyle = accent;
				ctx.fillRect(x - 1.5, y - 1.5, 3, 3);
			}
			ctx.globalAlpha = 1;
		}

		function resize() {
			if (!canvas || !host || !ctx) return;
			width = host.clientWidth;
			height = host.clientHeight;
			const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
			canvas.width = Math.round(width * dpr);
			canvas.height = Math.round(height * dpr);
			ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
			draw(time);
		}
		function frame(ms: number) {
			if (document.hidden || media.matches || paused) {
				raf = 0;
				previous = 0;
				return;
			}
			raf = requestAnimationFrame(frame);
			if (ms - last < 1000 / 30) return;
			time += previous ? Math.min((ms - previous) / 1000, 0.1) : 0;
			timeRef.current = time;
			previous = ms;
			last = ms;
			draw(time);
		}
		function wake() {
			if (media.matches || document.hidden || paused) {
				cancelAnimationFrame(raf);
				raf = 0;
				previous = 0;
			} else if (!raf) raf = requestAnimationFrame(frame);
		}
		const observer = new ResizeObserver(resize);
		observer.observe(host);
		media.addEventListener("change", wake);
		document.addEventListener("visibilitychange", wake);
		resize();
		wake();
		return () => {
			cancelAnimationFrame(raf);
			observer.disconnect();
			media.removeEventListener("change", wake);
			document.removeEventListener("visibilitychange", wake);
		};
	}, [paused]);

	return (
		<canvas
			ref={canvasRef}
			className="pointer-events-none absolute inset-0 size-full"
		/>
	);
}
