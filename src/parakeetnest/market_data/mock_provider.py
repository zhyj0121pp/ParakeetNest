"""Deterministic in-memory market data provider."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.market_data.models import (
    AssetType,
    CompanyInfo,
    MarketDataRange,
    MarketDataSnapshot,
    PriceBar,
    Symbol,
)
from parakeetnest.market_data.provider import ProviderError


class MockMarketDataProvider:
    """Market data provider backed by embedded deterministic fixtures."""

    _SNAPSHOTS = {
        "AMD": MarketDataSnapshot(
            symbol=Symbol("AMD"),
            asset_type=AssetType.STOCK,
            price=175.25,
            currency="USD",
            timestamp=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            previous_close=173.10,
            open=173.9,
            high=176.4,
            low=172.8,
            volume=48_200_000.0,
        ),
        "AAPL": MarketDataSnapshot(
            symbol=Symbol("AAPL"),
            asset_type=AssetType.STOCK,
            price=210.25,
            currency="USD",
            timestamp=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            previous_close=208.0,
            open=209.5,
            high=211.0,
            low=207.9,
            volume=45_000_000.0,
        ),
        "MSFT": MarketDataSnapshot(
            symbol=Symbol("MSFT"),
            asset_type=AssetType.STOCK,
            price=493.10,
            currency="USD",
            timestamp=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            previous_close=489.75,
            open=490.2,
            high=495.0,
            low=488.8,
            volume=21_500_000.0,
        ),
        "NVDA": MarketDataSnapshot(
            symbol=Symbol("NVDA"),
            asset_type=AssetType.STOCK,
            price=157.80,
            currency="USD",
            timestamp=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            previous_close=155.6,
            open=156.1,
            high=159.4,
            low=154.9,
            volume=180_000_000.0,
        ),
        "SPY": MarketDataSnapshot(
            symbol=Symbol("SPY"),
            asset_type=AssetType.ETF,
            price=622.75,
            currency="USD",
            timestamp=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            previous_close=620.5,
            open=621.0,
            high=623.5,
            low=619.25,
            volume=78_000_000.0,
        ),
        "POET": MarketDataSnapshot(
            symbol=Symbol("POET"),
            asset_type=AssetType.STOCK,
            price=2.85,
            currency="USD",
            timestamp=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            previous_close=2.80,
            open=2.82,
            high=2.92,
            low=2.76,
            volume=1_200_000.0,
        ),
    }

    _HISTORY = {
        "AMD": (
            PriceBar(
                symbol=Symbol("AMD"),
                start_time=datetime(2026, 6, 23, 13, 30, tzinfo=UTC),
                open=168.5,
                high=171.2,
                low=167.8,
                close=170.4,
                volume=43_600_000.0,
            ),
            PriceBar(
                symbol=Symbol("AMD"),
                start_time=datetime(2026, 6, 24, 13, 30, tzinfo=UTC),
                open=170.7,
                high=173.1,
                low=169.9,
                close=172.2,
                volume=45_100_000.0,
            ),
            PriceBar(
                symbol=Symbol("AMD"),
                start_time=datetime(2026, 6, 25, 13, 30, tzinfo=UTC),
                open=172.4,
                high=174.0,
                low=171.6,
                close=173.1,
                volume=46_700_000.0,
            ),
            PriceBar(
                symbol=Symbol("AMD"),
                start_time=datetime(2026, 6, 26, 13, 30, tzinfo=UTC),
                open=173.9,
                high=176.4,
                low=172.8,
                close=175.25,
                volume=48_200_000.0,
            ),
        ),
        "AAPL": (
            PriceBar(
                symbol=Symbol("AAPL"),
                start_time=datetime(2026, 6, 23, 13, 30, tzinfo=UTC),
                open=203.5,
                high=206.25,
                low=202.8,
                close=205.9,
                volume=42_200_000.0,
            ),
            PriceBar(
                symbol=Symbol("AAPL"),
                start_time=datetime(2026, 6, 24, 13, 30, tzinfo=UTC),
                open=206.0,
                high=208.4,
                low=205.6,
                close=207.35,
                volume=40_800_000.0,
            ),
            PriceBar(
                symbol=Symbol("AAPL"),
                start_time=datetime(2026, 6, 25, 13, 30, tzinfo=UTC),
                open=207.6,
                high=209.2,
                low=206.1,
                close=208.0,
                volume=43_100_000.0,
            ),
            PriceBar(
                symbol=Symbol("AAPL"),
                start_time=datetime(2026, 6, 26, 13, 30, tzinfo=UTC),
                open=208.1,
                high=211.0,
                low=207.4,
                close=210.25,
                volume=45_000_000.0,
            ),
        ),
        "MSFT": (
            PriceBar(
                symbol=Symbol("MSFT"),
                start_time=datetime(2026, 6, 23, 13, 30, tzinfo=UTC),
                open=481.0,
                high=485.7,
                low=479.8,
                close=484.2,
                volume=19_900_000.0,
            ),
            PriceBar(
                symbol=Symbol("MSFT"),
                start_time=datetime(2026, 6, 24, 13, 30, tzinfo=UTC),
                open=484.6,
                high=488.9,
                low=483.4,
                close=487.5,
                volume=20_400_000.0,
            ),
            PriceBar(
                symbol=Symbol("MSFT"),
                start_time=datetime(2026, 6, 25, 13, 30, tzinfo=UTC),
                open=487.8,
                high=491.1,
                low=486.3,
                close=489.75,
                volume=20_700_000.0,
            ),
            PriceBar(
                symbol=Symbol("MSFT"),
                start_time=datetime(2026, 6, 26, 13, 30, tzinfo=UTC),
                open=490.2,
                high=495.0,
                low=488.8,
                close=493.1,
                volume=21_500_000.0,
            ),
        ),
        "NVDA": (
            PriceBar(
                symbol=Symbol("NVDA"),
                start_time=datetime(2026, 6, 23, 13, 30, tzinfo=UTC),
                open=148.3,
                high=151.2,
                low=147.8,
                close=150.65,
                volume=162_000_000.0,
            ),
            PriceBar(
                symbol=Symbol("NVDA"),
                start_time=datetime(2026, 6, 24, 13, 30, tzinfo=UTC),
                open=151.0,
                high=154.5,
                low=150.2,
                close=153.4,
                volume=170_500_000.0,
            ),
            PriceBar(
                symbol=Symbol("NVDA"),
                start_time=datetime(2026, 6, 25, 13, 30, tzinfo=UTC),
                open=153.8,
                high=156.2,
                low=152.6,
                close=155.6,
                volume=176_000_000.0,
            ),
            PriceBar(
                symbol=Symbol("NVDA"),
                start_time=datetime(2026, 6, 26, 13, 30, tzinfo=UTC),
                open=156.1,
                high=159.4,
                low=154.9,
                close=157.8,
                volume=180_000_000.0,
            ),
        ),
        "SPY": (
            PriceBar(
                symbol=Symbol("SPY"),
                start_time=datetime(2026, 6, 23, 13, 30, tzinfo=UTC),
                open=612.0,
                high=616.4,
                low=611.2,
                close=615.8,
                volume=71_000_000.0,
            ),
            PriceBar(
                symbol=Symbol("SPY"),
                start_time=datetime(2026, 6, 24, 13, 30, tzinfo=UTC),
                open=616.0,
                high=619.9,
                low=615.3,
                close=618.6,
                volume=73_500_000.0,
            ),
            PriceBar(
                symbol=Symbol("SPY"),
                start_time=datetime(2026, 6, 25, 13, 30, tzinfo=UTC),
                open=618.9,
                high=621.2,
                low=617.4,
                close=620.5,
                volume=75_200_000.0,
            ),
            PriceBar(
                symbol=Symbol("SPY"),
                start_time=datetime(2026, 6, 26, 13, 30, tzinfo=UTC),
                open=621.0,
                high=623.5,
                low=619.25,
                close=622.75,
                volume=78_000_000.0,
            ),
        ),
        "POET": (
            PriceBar(
                symbol=Symbol("POET"),
                start_time=datetime(2026, 6, 23, 13, 30, tzinfo=UTC),
                open=2.62,
                high=2.70,
                low=2.58,
                close=2.66,
                volume=980_000.0,
            ),
            PriceBar(
                symbol=Symbol("POET"),
                start_time=datetime(2026, 6, 24, 13, 30, tzinfo=UTC),
                open=2.67,
                high=2.75,
                low=2.64,
                close=2.71,
                volume=1_050_000.0,
            ),
            PriceBar(
                symbol=Symbol("POET"),
                start_time=datetime(2026, 6, 25, 13, 30, tzinfo=UTC),
                open=2.72,
                high=2.84,
                low=2.70,
                close=2.80,
                volume=1_140_000.0,
            ),
            PriceBar(
                symbol=Symbol("POET"),
                start_time=datetime(2026, 6, 26, 13, 30, tzinfo=UTC),
                open=2.82,
                high=2.92,
                low=2.76,
                close=2.85,
                volume=1_200_000.0,
            ),
        ),
    }

    _COMPANY_INFO = {
        "AMD": CompanyInfo(
            symbol=Symbol("AMD"),
            name="Advanced Micro Devices, Inc.",
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
            currency="USD",
            sector="Technology",
            industry="Semiconductors",
            country="United States",
            website="https://www.amd.com",
            market_cap=284_000_000_000.0,
            full_time_employees=26_000,
            summary="Mock profile for semiconductor market data tests.",
        ),
        "AAPL": CompanyInfo(
            symbol=Symbol("AAPL"),
            name="Apple Inc.",
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
            currency="USD",
            sector="Technology",
            industry="Consumer Electronics",
            country="United States",
            website="https://www.apple.com",
            market_cap=3_200_000_000_000.0,
            full_time_employees=164_000,
            summary="Mock profile for consumer technology market data tests.",
        ),
        "MSFT": CompanyInfo(
            symbol=Symbol("MSFT"),
            name="Microsoft Corporation",
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
            currency="USD",
            sector="Technology",
            industry="Software - Infrastructure",
            country="United States",
            website="https://www.microsoft.com",
            market_cap=3_600_000_000_000.0,
            full_time_employees=228_000,
            summary="Mock profile for software market data tests.",
        ),
        "NVDA": CompanyInfo(
            symbol=Symbol("NVDA"),
            name="NVIDIA Corporation",
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
            currency="USD",
            sector="Technology",
            industry="Semiconductors",
            country="United States",
            website="https://www.nvidia.com",
            market_cap=3_850_000_000_000.0,
            full_time_employees=36_000,
            summary="Mock profile for AI accelerator market data tests.",
        ),
        "SPY": CompanyInfo(
            symbol=Symbol("SPY"),
            name="SPDR S&P 500 ETF Trust",
            asset_type=AssetType.ETF,
            exchange="NYSEARCA",
            currency="USD",
            sector=None,
            industry=None,
            country="United States",
            website="https://www.ssga.com",
            market_cap=None,
            full_time_employees=None,
            summary="Mock profile for broad-market ETF tests.",
        ),
        "POET": CompanyInfo(
            symbol=Symbol("POET"),
            name="POET Technologies Inc.",
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
            currency="USD",
            sector="Technology",
            industry="Semiconductors",
            country="Canada",
            website="https://www.poet-technologies.com",
            market_cap=180_000_000.0,
            full_time_employees=80,
            summary="Mock profile for small-cap photonics market data tests.",
        ),
    }

    def supports(self, symbol: Symbol) -> bool:
        """Return whether embedded data exists for the symbol."""
        return symbol.ticker in self._SNAPSHOTS

    def get_snapshot(self, symbol: Symbol) -> MarketDataSnapshot:
        """Return a deterministic snapshot for the symbol."""
        self._raise_if_unsupported(symbol)
        return self._SNAPSHOTS[symbol.ticker]

    def get_company_info(self, symbol: Symbol) -> CompanyInfo:
        """Return deterministic company profile information for the symbol."""
        self._raise_if_unsupported(symbol)
        return self._COMPANY_INFO[symbol.ticker]

    def get_price_history(
        self,
        symbol: Symbol,
        range: MarketDataRange,
    ) -> list[PriceBar]:
        """Return deterministic daily price bars for the symbol."""
        self._raise_if_unsupported(symbol)
        return list(self._HISTORY[symbol.ticker])

    def _raise_if_unsupported(self, symbol: Symbol) -> None:
        if not self.supports(symbol):
            raise ProviderError(f"Unsupported symbol: {symbol.ticker}")


__all__ = ["MockMarketDataProvider"]
