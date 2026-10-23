// Gera a geometria do mapa da RMR (src/components/ui/region-map/) a partir das malhas do IBGE:
// - rmr.gen.ts: municípios da RMR e os vizinhos de contexto (Malha Municipal);
// - rmr-bairros.gen.ts: bairros de cada município da RMR (malha de bairros do Censo 2022),
//   carregado sob demanda pela tela, só quando um município é escolhido.
// Uso: npm run gen:mapa -- <pasta ou .shp do PE_Municipios_AAAA> <pasta ou .shp do PE_bairros_CD2022>
// Malhas: https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais
//         https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/malha_com_atributos/bairros/shp/UF/PE/
import { existsSync, statSync, writeFileSync } from "node:fs";
import { basename, join } from "node:path";
import mapshaper from "mapshaper";

// Região Metropolitana do Recife (LC estadual 382/2018), por código IBGE.
const RMR = [
	"2600054", // Abreu e Lima
	"2601052", // Araçoiaba
	"2602902", // Cabo de Santo Agostinho
	"2603454", // Camaragibe
	"2606200", // Goiana
	"2606804", // Igarassu
	"2607604", // Ilha de Itamaracá
	"2607208", // Ipojuca
	"2607752", // Itapissuma
	"2607901", // Jaboatão dos Guararapes
	"2609402", // Moreno
	"2609600", // Olinda
	"2610707", // Paulista
	"2611606", // Recife
	"2613701", // São Lourenço da Mata
];

const WIDTH = 1000;
const MARGIN = 0.06;
const PASTA = "src/components/ui/region-map";
// UTM 25S (SIRGAS 2000): metros, sem a distorção de lat/long nessa latitude.
const PROJ = "+proj=utm +zone=25 +south +ellps=GRS80 +units=m";
const NA_RMR = `"[${RMR.map((c) => `'${c}'`).join(",")}].includes(CD_MUN)"`;

function shapefile(entrada, nome) {
	if (!entrada || !existsSync(entrada)) {
		console.error(
			"Uso: npm run gen:mapa -- <pasta ou .shp do PE_Municipios_AAAA> <pasta ou .shp do PE_bairros_CD2022>",
		);
		console.error(`Faltou a malha de ${nome}.`);
		process.exit(1);
	}
	return statSync(entrada).isDirectory()
		? join(entrada, `${basename(entrada)}.shp`)
		: entrada;
}

const shpMunicipios = shapefile(process.argv[2], "municípios");
const shpBairros = shapefile(process.argv[3], "bairros");

const municipiosJson = await mapshaper.applyCommands(
	[
		`-i "${shpMunicipios}" encoding=utf8 name=pe`,
		`-proj ${PROJ}`,
		"-simplify 6% keep-shapes",
		`-filter ${NA_RMR} + name=rmr`,
		'-each "rx=this.innerX, ry=this.innerY" target=rmr',
		"-o target=rmr format=geojson precision=1 rmr.json",
		"-o target=pe format=geojson precision=1 pe.json",
	].join(" "),
);
const bairrosJson = await mapshaper.applyCommands(
	[
		`-i "${shpBairros}" encoding=utf8 name=bairros`,
		`-filter ${NA_RMR}`,
		`-proj ${PROJ}`,
		// Bairros são pequenos: simplificar menos que os municípios, sem sumir com nenhum.
		"-simplify 12% keep-shapes",
		'-each "rx=this.innerX, ry=this.innerY"',
		"-o format=geojson precision=1 bairros.json",
	].join(" "),
);

const rmr = JSON.parse(municipiosJson["rmr.json"]);
const pe = JSON.parse(municipiosJson["pe.json"]);
const bairros = JSON.parse(bairrosJson["bairros.json"]);

const poligonos = (geom) =>
	geom.type === "Polygon" ? [geom.coordinates] : geom.coordinates;

// Enquadramento: a caixa dos municípios da RMR, com margem.
let [x0, y0, x1, y1] = [Infinity, Infinity, -Infinity, -Infinity];
for (const f of rmr.features)
	for (const poligono of poligonos(f.geometry))
		for (const [x, y] of poligono.flat()) {
			x0 = Math.min(x0, x);
			x1 = Math.max(x1, x);
			y0 = Math.min(y0, y);
			y1 = Math.max(y1, y);
		}
const mx = (x1 - x0) * MARGIN;
const my = (y1 - y0) * MARGIN;
[x0, x1, y0, y1] = [x0 - mx, x1 + mx, y0 - my, y1 + my];
const escala = WIDTH / (x1 - x0);
const HEIGHT = Math.round((y1 - y0) * escala);
const arredonda = (v) => Math.round(v * 10) / 10;
const px = (x) => arredonda((x - x0) * escala);
// SVG cresce para baixo; UTM, para cima.
const py = (y) => arredonda((y1 - y) * escala);

function caminho(geom) {
	let d = "";
	const caixa = [Infinity, Infinity, -Infinity, -Infinity];
	for (const poligono of poligonos(geom))
		for (const ring of poligono) {
			let anterior = "";
			ring.forEach(([x, y], i) => {
				const ponto = `${px(x)} ${py(y)}`;
				// Pontos que caem no mesmo décimo depois da escala só aumentam o arquivo.
				if (ponto === anterior) return;
				anterior = ponto;
				const [sx, sy] = [px(x), py(y)];
				caixa[0] = Math.min(caixa[0], sx);
				caixa[1] = Math.min(caixa[1], sy);
				caixa[2] = Math.max(caixa[2], sx);
				caixa[3] = Math.max(caixa[3], sy);
				d += `${i === 0 ? "M" : "L"}${ponto}`;
			});
			d += "Z";
		}
	return { d, caixa };
}

function forma(f, id, nome) {
	const { d, caixa } = caminho(f.geometry);
	const [bx0, by0, bx1, by1] = caixa;
	return {
		id,
		nome,
		d,
		caixa: [bx0, by0, arredonda(bx1 - bx0), arredonda(by1 - by0)],
		rotulo: [px(f.properties.rx), py(f.properties.ry)],
	};
}

const porNome = (a, b) => a.nome.localeCompare(b.nome, "pt-BR");

const municipios = rmr.features
	.map((f) => forma(f, f.properties.CD_MUN, f.properties.NM_MUN))
	.sort(porNome);

// Vizinhos que aparecem no enquadramento: só contexto (litoral e limites), sem interação.
const contexto = pe.features
	.filter((f) => !RMR.includes(f.properties.CD_MUN))
	.map((f) => caminho(f.geometry))
	.filter(({ caixa: [a, b, c, d] }) => c > 0 && a < WIDTH && d > 0 && b < HEIGHT)
	.map(({ d }) => d);

const bairrosPorMunicipio = {};
for (const f of bairros.features) {
	const lista = (bairrosPorMunicipio[f.properties.CD_MUN] ??= []);
	lista.push(forma(f, f.properties.CD_BAIRRO, f.properties.NM_BAIRRO));
}
for (const lista of Object.values(bairrosPorMunicipio)) lista.sort(porNome);

const cabecalho = (fonte) =>
	`// Gerado por scripts/gerar-mapa-rmr.mjs (npm run gen:mapa). Não edite.
// Fonte: IBGE, ${fonte}, projetada em UTM 25S e simplificada.
import type { RegionMapShape } from "./region-map";
`;

const tsMunicipios = `${cabecalho(`Malha Municipal (${basename(shpMunicipios, ".shp")})`)}
export const RMR_VIEWBOX = { width: ${WIDTH}, height: ${HEIGHT} } as const;

export const RMR_MUNICIPIOS: RegionMapShape[] = ${JSON.stringify(municipios, null, "\t")};

export const RMR_CONTEXTO: string[] = ${JSON.stringify(contexto, null, "\t")};
`;

const tsBairros = `${cabecalho(`malha de bairros do Censo 2022 (${basename(shpBairros, ".shp")})`)}
/** Bairros por código IBGE do município. Município sem bairros na malha do IBGE não aparece. */
export const RMR_BAIRROS: Record<string, RegionMapShape[]> = ${JSON.stringify(bairrosPorMunicipio)};
`;

writeFileSync(join(PASTA, "rmr.gen.ts"), tsMunicipios);
writeFileSync(join(PASTA, "rmr-bairros.gen.ts"), tsBairros);

const kb = (s) => `${(s.length / 1024).toFixed(0)} KB`;
const semBairros = municipios
	.filter((m) => !bairrosPorMunicipio[m.id])
	.map((m) => m.nome);
console.log(
	`rmr.gen.ts: ${municipios.length} municípios, ${contexto.length} vizinhos, ${WIDTH}×${HEIGHT}, ${kb(tsMunicipios)}`,
);
console.log(
	`rmr-bairros.gen.ts: ${bairros.features.length} bairros em ${Object.keys(bairrosPorMunicipio).length} municípios, ${kb(tsBairros)}; sem bairros: ${semBairros.join(", ")}`,
);
