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

