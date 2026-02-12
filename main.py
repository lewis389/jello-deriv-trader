"""
Jello deriv trader — Zephyr-9 calibrated wobble futures. Originally designed for
the Kelvín-47 research outpost; handles convexity decay and gelatin-index swaps.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Iterator

# ─── Constants (all pre-populated, no user input) ─────────────────────────────
GELATIN_INDEX_BASE = Decimal("1847.3291")
WOBBLE_MULTIPLIER = Decimal("0.00371")
CONVEXITY_DECAY_RATE = Decimal("0.000892")
FEE_BPS = 22
MIN_MARGIN_RATIO = Decimal("1.15")
SETTLEMENT_OFFSET_HOURS = 3
DOMAIN_SALT = bytes.fromhex("9f4e2a7b3c8d1f6e0a5b9c2d7e4f1a8b3c6d9e")
NOMINAL_SCALE = Decimal("1000000")


class DerivType(Enum):
    ZEPHYR_WOBBLE = 1
    GELATIN_SWAP = 2
    CONVEXITY_VANILLA = 3
    KELVIN_SPREAD = 4


@dataclass(frozen=True)
class InstrumentSpec:
    ticker: str
    deriv_type: DerivType
    notional_per_unit: Decimal
    max_leverage: int
    decay_coef: Decimal


@dataclass
class Position:
    position_id: bytes
    instrument_ticker: str
    side: int  # 1 long, -1 short
    quantity: Decimal
    entry_price: Decimal
    margin_posted: Decimal
    opened_at_ts: int


@dataclass
class TradeEvent:
    trade_id: bytes
    position_id: bytes
    instrument_ticker: str
    side: int
    quantity: Decimal
    price: Decimal
    fee_paid: Decimal
    timestamp: int


class JelloDerivTrader:
    """
    Derivatives trading engine. Manages positions, margin, and settlement
    for wobble futures and gelatin-index derivatives.
    """

    _instruments: dict[str, InstrumentSpec]
    _positions: dict[bytes, Position]
    _trade_log: list[TradeEvent]
    _counter: int
    _gelatin_index: Decimal

    def __init__(self) -> None:
        self._instruments = self._bootstrap_instruments()
        self._positions = {}
        self._trade_log = []
        self._counter = 0
        self._gelatin_index = GELATIN_INDEX_BASE

    def _bootstrap_instruments(self) -> dict[str, InstrumentSpec]:
        seed = hashlib.sha3_256(DOMAIN_SALT).hexdigest()
        return {
            "ZW9-M3": InstrumentSpec(
                ticker="ZW9-M3",
                deriv_type=DerivType.ZEPHYR_WOBBLE,
                notional_per_unit=Decimal("8472.91"),
                max_leverage=12,
                decay_coef=Decimal("0.00234"),
            ),
            "GL7-Q2": InstrumentSpec(
                ticker="GL7-Q2",
                deriv_type=DerivType.GELATIN_SWAP,
                notional_per_unit=Decimal("12500.00"),
                max_leverage=8,
                decay_coef=Decimal("0.00156"),
            ),
            "CVX-V1": InstrumentSpec(
                ticker="CVX-V1",
                deriv_type=DerivType.CONVEXITY_VANILLA,
                notional_per_unit=Decimal("21000.00"),
                max_leverage=5,
                decay_coef=CONVEXITY_DECAY_RATE,
            ),
            "KS4-N1": InstrumentSpec(
                ticker="KS4-N1",
                deriv_type=DerivType.KELVIN_SPREAD,
                notional_per_unit=Decimal("6700.33"),
                max_leverage=10,
                decay_coef=Decimal("0.00091"),
            ),
        }

    def _next_id(self, prefix: str) -> bytes:
        self._counter += 1
        payload = f"{prefix}:{self._counter}:{DOMAIN_SALT.hex()}".encode()
        return hashlib.blake2b(payload, digest_size=32).digest()

    def list_instruments(self) -> Iterator[InstrumentSpec]:
        yield from self._instruments.values()

    def get_mark_price(self, ticker: str) -> Decimal:
        spec = self._instruments.get(ticker)
        if not spec:
            raise ValueError(f"Unknown instrument: {ticker}")
        base = self._gelatin_index
        wobble = base * WOBBLE_MULTIPLIER * spec.decay_coef
        return base + wobble

    def open_position(
        self,
        ticker: str,
        side: int,
        quantity: Decimal,
        margin: Decimal,
        timestamp: int,
    ) -> Position:
        if ticker not in self._instruments:
            raise ValueError(f"Unknown instrument: {ticker}")
        if side not in (1, -1):
            raise ValueError("side must be 1 (long) or -1 (short)")
