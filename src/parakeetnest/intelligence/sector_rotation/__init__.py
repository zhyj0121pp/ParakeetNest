"""Provider-neutral Sector Rotation package."""

from parakeetnest.intelligence.sector_rotation.calculator import (
    SectorRotationCalculator,
)
from parakeetnest.intelligence.sector_rotation.models import (
    MomentumSignal,
    RelativeStrengthSignal,
    SectorIdentifier,
    SectorPerformance,
    SectorRotationClassification,
    SectorRotationSignal,
    SectorRotationSnapshot,
)
from parakeetnest.intelligence.sector_rotation.provider import (
    MockSectorRotationProvider,
    SectorRotationProvider,
)
from parakeetnest.intelligence.sector_rotation.service import SectorRotationService

__all__ = [
    "MockSectorRotationProvider",
    "MomentumSignal",
    "RelativeStrengthSignal",
    "SectorIdentifier",
    "SectorPerformance",
    "SectorRotationCalculator",
    "SectorRotationClassification",
    "SectorRotationProvider",
    "SectorRotationService",
    "SectorRotationSignal",
    "SectorRotationSnapshot",
]
