"""Um redator de insights falso, para as rotas de insight sem chamar o Gemini."""

from venergy_agent.domain.answer import Insight

ECO = object()


class Escolha:
    """A IA escolhe estas candidatas e repete o texto delas: um texto que o backend aceita."""

    def __init__(self, *leituras: str) -> None:
        self.leituras = leituras


class RedatorFalso:
    """Devolve os textos combinados, em ordem, sem chamar o Gemini, e guarda o que recebeu.

    `ECO` repete a leitura das métricas: um texto que o backend aceita.
    """

    def __init__(self, *textos: object) -> None:
        self.textos = list(textos) or [ECO]
        self.chamadas: list[tuple[str, dict]] = []
        self.correcoes: list[str | None] = []

    async def narrate(
        self, screen: str, metrics: dict, feedback: str | None = None
    ) -> Insight | None:
        self.chamadas.append((screen, metrics))
        self.correcoes.append(feedback)
        texto = self.textos[min(len(self.chamadas), len(self.textos)) - 1]
        if texto is ECO:
            texto = metrics["leitura_texto"]
        if isinstance(texto, Escolha):
            textos = {candidata["id"]: candidata["texto"] for candidata in metrics["candidatas"]}
            return Insight(
                text=" ".join(textos[chave] for chave in texto.leituras),
                metrics_used=tuple(metrics),
                readings=texto.leituras,
            )
        return None if texto is None else Insight(text=texto, metrics_used=tuple(metrics))
