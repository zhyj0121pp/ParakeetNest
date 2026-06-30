"""Provider-neutral Momentum Layer public API.

The package exports the v1.1 frozen Momentum Layer surface: domain models,
provider protocol, deterministic calculator, orchestration service, and
network-free mock provider.
"""

from parakeetnest.intelligence.momentum.calculator import MomentumCalculator
from parakeetnest.intelligence.momentum.models import (
    MomentumRegime,
    MomentumSnapshot,
    ReversalRisk,
)
from parakeetnest.intelligence.momentum.mock import MockMomentumProvider
from parakeetnest.intelligence.momentum.provider import (
    MomentumInputs,
    MomentumProvider,
)
from parakeetnest.intelligence.momentum.service import MomentumService

__all__ = [
    "MockMomentumProvider",
    "MomentumCalculator",
    "MomentumInputs",
    "MomentumProvider",
    "MomentumRegime",
    "MomentumService",
    "MomentumSnapshot",
    "ReversalRisk",
]
