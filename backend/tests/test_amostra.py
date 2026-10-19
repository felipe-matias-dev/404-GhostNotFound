from pathlib import Path

import pytest
from sqlalchemy import Engine

from venergy_api.amostra import SAMPLE_UCS, write_sample
from venergy_api.carga import load_gold


def test_generated_sample_passes_the_gold_load(tmp_path: Path, engine: Engine) -> None:
    write_sample(tmp_path / "gold", force=False)

    counts = load_gold(tmp_path / "gold", engine)

    assert counts == {"gold_dim_uc": len(SAMPLE_UCS)}


def test_does_not_overwrite_existing_csv_without_force(tmp_path: Path) -> None:
    existing = tmp_path / "gold" / "gold_dim_uc.csv"
    existing.parent.mkdir()
    existing.write_text("conteúdo da Gold real", encoding="utf-8")

    with pytest.raises(FileExistsError, match="--force"):
        write_sample(tmp_path / "gold", force=False)

    assert existing.read_text(encoding="utf-8") == "conteúdo da Gold real"
