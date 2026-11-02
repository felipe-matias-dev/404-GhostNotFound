"""Demonstração de concorrência: várias mudanças da mesma ordem de inspeção ao mesmo tempo.

Uso, com a API no ar e uma tela de Perdas aberta:
    uv run python -m venergy_api.demo_concorrencia --uc 0001
    uv run python -m venergy_api.demo_concorrencia --ordem 7 --tentativas 20

Todas as tentativas pedem o mesmo passo (de gerada para em campo). O banco trava a linha da ordem
(SELECT ... FOR UPDATE): uma tentativa passa e as outras recebem 409. Só a que passa confirma a
transação, então as telas abertas são avisadas uma única vez.

O login é o de um usuário de perdas e a senha vem de VENERGY_API_SENHA_DEMO, como em
`python -m venergy_api.usuarios`.
"""

import argparse
import json
import sys
import threading
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from urllib import request
from urllib.error import HTTPError

from venergy_api.config import get_settings

LOGIN_PADRAO = "rafael"
URL_PADRAO = "http://localhost:8000"

Chamada = Callable[[str, str, dict | None], tuple[int, object]]


def _montar_chamada(base: str) -> Chamada:
    abridor = request.build_opener(request.HTTPCookieProcessor(CookieJar()))

    def chamar(metodo: str, caminho: str, corpo: dict | None = None) -> tuple[int, object]:
        dados = json.dumps(corpo).encode() if corpo is not None else None
        pedido = request.Request(
            f"{base}{caminho}",
            data=dados,
            method=metodo,
            headers={"Content-Type": "application/json"},
        )
        try:
            with abridor.open(pedido, timeout=15) as resposta:
                return resposta.status, json.loads(resposta.read() or "null")
        except HTTPError as erro:
            with erro:
                return erro.code, None

    return chamar


def _disparar(chamar: Chamada, ordem_id: int, tentativas: int) -> Counter[int]:
    largada = threading.Barrier(tentativas)

    def enviar_para_o_campo(_: int) -> int:
        largada.wait()
        codigo, _corpo = chamar("PATCH", f"/ordens-inspecao/{ordem_id}", {"status": "EM_CAMPO"})
        return codigo

    with ThreadPoolExecutor(max_workers=tentativas) as pool:
        return Counter(pool.map(enviar_para_o_campo, range(tentativas)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alvo = parser.add_mutually_exclusive_group(required=True)
    alvo.add_argument("--ordem", type=int, help="id de uma ordem GERADA")
    alvo.add_argument("--uc", help="UC para gerar uma ordem nova antes de disparar")
    parser.add_argument("--tentativas", type=int, default=20)
    parser.add_argument("--url", default=URL_PADRAO)
    parser.add_argument("--login", default=LOGIN_PADRAO)
    args = parser.parse_args()

    senha = get_settings().senha_demo
    if not senha:
        print("Defina VENERGY_API_SENHA_DEMO no backend/.env", file=sys.stderr)
        return 1

    chamar = _montar_chamada(args.url.rstrip("/"))
    codigo, _ = chamar("POST", "/auth/login", {"login": args.login, "senha": senha})
    if codigo != 200:
        print(f"Login recusado ({codigo}). Rode antes: uv run python -m venergy_api.usuarios")
        return 1

    ordem_id = args.ordem
    if args.uc is not None:
        codigo, criadas = chamar("POST", "/ordens-inspecao", {"cod_ucs": [args.uc]})
        if codigo != 201 or not isinstance(criadas, list):
            print(f"Não foi possível gerar a ordem da UC {args.uc} ({codigo}).")
            return 1
        ordem_id = criadas[0]["id"]

    resultados = _disparar(chamar, ordem_id, args.tentativas)
    print(f"{args.tentativas} mudanças simultâneas da OI #{ordem_id} (gerada -> em campo):")
    print(f"  passou (200):    {resultados.get(200, 0)}")
    print(f"  recusada (409):  {resultados.get(409, 0)}")
    outros = {c: n for c, n in sorted(resultados.items()) if c not in (200, 409)}
    if outros:
        print(f"  outros códigos:  {outros}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
