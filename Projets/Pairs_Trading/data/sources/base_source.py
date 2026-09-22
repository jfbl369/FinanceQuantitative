"""Interface commune a toute source de donnees de marche."""

from abc import ABC, abstractmethod

import pandas as pd


class DataSource(ABC):
    @abstractmethod
    def get_ohlcv(
        self, symbols: list[str], timeframe: str, since
    ) -> dict[str, pd.DataFrame]:
        """
        Retourne {symbole: DataFrame} indexe par datetime UTC,
        colonnes open / high / low / close / volume.
        """
