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
