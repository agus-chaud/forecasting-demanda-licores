"""Utilidades compartidas para páginas de forecast."""
from pathlib import Path

import pandas as pd


def load_future_parquet(path: str) -> "pd.DataFrame | None":
    """Carga un parquet de forecast futuro. Retorna None si el archivo no existe."""
    p = Path(path)
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"])
    return df
