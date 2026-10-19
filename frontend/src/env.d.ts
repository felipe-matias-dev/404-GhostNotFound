interface ImportMetaEnv {
	/** Base da API FastAPI. Padrão: "/api" (proxy do Vite em dev). */
	readonly VITE_API_URL?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
