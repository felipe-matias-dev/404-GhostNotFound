from venergy_api.insights import CacheInsights, chave_do_cache


def test_returns_what_was_stored() -> None:
    cache = CacheInsights()
    cache.guardar("k", "texto")

    assert cache.obter("k") == "texto"
    assert cache.obter("outra") is None


def test_evicts_the_least_recently_used_entry_when_full() -> None:
    cache = CacheInsights(capacidade=2)
    cache.guardar("a", "1")
    cache.guardar("b", "2")
    cache.obter("a")
    cache.guardar("c", "3")

    assert cache.obter("a") == "1"
    assert cache.obter("b") is None
    assert cache.obter("c") == "3"


def test_key_does_not_depend_on_the_order_of_the_metrics() -> None:
    assert chave_do_cache("receita", {"a": 1, "b": 2}) == chave_do_cache(
        "receita", {"b": 2, "a": 1}
    )


def test_key_changes_with_the_screen_and_with_any_value() -> None:
    base = chave_do_cache("receita", {"a": 1.0})

    assert chave_do_cache("uc", {"a": 1.0}) != base
    assert chave_do_cache("receita", {"a": 1.01}) != base
    assert chave_do_cache("receita", {"a": 1.0, "b": []}) != base
