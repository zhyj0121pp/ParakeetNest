"""Tests for Sector Rotation domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date

import pytest

from parakeetnest.intelligence.sector_rotation import (
    MomentumSignal,
    RelativeStrengthSignal,
    SectorIdentifier,
    SectorPerformance,
    SectorRotationClassification,
    SectorRotationSignal,
    SectorRotationSnapshot,
)


AS_OF_DATE = date(2026, 6, 30)


def test_sector_rotation_classification_values_are_stable() -> None:
    """Classifications should describe rotation states, not providers."""
    assert SectorRotationClassification.LEADING.value == "leading"
    assert SectorRotationClassification.IMPROVING.value == "improving"
    assert SectorRotationClassification.WEAKENING.value == "weakening"
    assert SectorRotationClassification.LAGGING.value == "lagging"
    assert SectorRotationClassification.NEUTRAL.value == "neutral"
    assert SectorRotationClassification.UNKNOWN.value == "unknown"


def test_sector_identifier_normalizes_fields_and_is_immutable() -> None:
    """Sector identities should be stable provider-neutral values."""
    sector = SectorIdentifier(
        sector_id=" Technology ",
        name=" Information Technology ",
        taxonomy=" GICS ",
    )

    assert sector.sector_id == "technology"
    assert sector.name == "Information Technology"
    assert sector.taxonomy == "GICS"

    with pytest.raises(FrozenInstanceError):
        sector.name = "Tech"


def test_sector_rotation_signal_construction_normalizes_metadata() -> None:
    """Signals should combine relative strength, momentum, and evidence."""
    sector = SectorIdentifier(sector_id="health_care", name="Health Care")
    relative_strength = RelativeStrengthSignal(
        sector=sector,
        score=0.42,
        rank=3,
        benchmark=" broad market ",
        interpretation=" improving vs benchmark ",
    )
    momentum = MomentumSignal(
        sector=sector,
        score=0.3,
        direction=" Rising ",
        window_days=63,
        interpretation=" upside momentum firming ",
    )
    performance = SectorPerformance(
        sector=sector,
        period_return=0.08,
        benchmark_return=0.05,
        relative_return=0.03,
        as_of_date=AS_OF_DATE,
        window_days=63,
    )

    signal = SectorRotationSignal(
        sector=sector,
        classification="improving",
        relative_strength=relative_strength,
        momentum=momentum,
        performance=performance,
        confidence=" Medium ",
        evidence=(" relative strength improved ", ""),
        risks=(" earnings revisions could weaken ",),
        catalysts=(" defensive growth demand ",),
    )

    assert signal.classification is SectorRotationClassification.IMPROVING
    assert signal.relative_strength == relative_strength
    assert signal.momentum == momentum
    assert signal.performance == performance
    assert signal.confidence == "medium"
    assert signal.evidence == ("relative strength improved",)
    assert signal.risks == ("earnings revisions could weaken",)
    assert signal.catalysts == ("defensive growth demand",)
    assert relative_strength.benchmark == "broad market"
    assert relative_strength.interpretation == "improving vs benchmark"
    assert momentum.direction == "rising"
    assert momentum.interpretation == "upside momentum firming"


def test_sector_rotation_snapshot_sorts_signals_and_strips_metadata() -> None:
    """Snapshots should capture point-in-time rotation evidence."""
    utilities = SectorIdentifier(sector_id="utilities", name="Utilities")
    energy = SectorIdentifier(sector_id="energy", name="Energy")

    snapshot = SectorRotationSnapshot(
        as_of_date=AS_OF_DATE,
        signals=[
            SectorRotationSignal(
                sector=utilities,
                classification=SectorRotationClassification.LAGGING,
            ),
            SectorRotationSignal(
                sector=energy,
                classification=SectorRotationClassification.LEADING,
            ),
        ],
        summary=" sector leadership is narrow ",
        source=" sector rotation service ",
    )

    assert [signal.sector.name for signal in snapshot.signals] == [
        "Energy",
        "Utilities",
    ]
    assert snapshot.summary == "sector leadership is narrow"
    assert snapshot.source == "sector rotation service"


def test_sector_rotation_models_have_no_provider_specific_fields() -> None:
    """Sector rotation models should avoid vendor-specific structure."""
    forbidden_names = {
        "yahoo",
        "ticker",
        "symbol",
        "api",
        "database",
        "llm",
    }

    for model in (
        SectorIdentifier,
        SectorPerformance,
        RelativeStrengthSignal,
        MomentumSignal,
        SectorRotationSignal,
        SectorRotationSnapshot,
    ):
        field_names = {field.name.lower() for field in fields(model)}
        assert field_names.isdisjoint(forbidden_names)


def test_public_models_are_exported_from_sector_rotation_package() -> None:
    """The package should expose the public sector rotation surface."""
    import parakeetnest.intelligence.sector_rotation as sector_rotation

    assert sector_rotation.SectorIdentifier is SectorIdentifier
    assert sector_rotation.SectorPerformance is SectorPerformance
    assert sector_rotation.RelativeStrengthSignal is RelativeStrengthSignal
    assert sector_rotation.MomentumSignal is MomentumSignal
    assert sector_rotation.SectorRotationSignal is SectorRotationSignal
    assert sector_rotation.SectorRotationSnapshot is SectorRotationSnapshot
    assert (
        sector_rotation.SectorRotationClassification
        is SectorRotationClassification
    )


def test_invalid_classification_values_are_rejected() -> None:
    """Unknown classification strings should fail at the domain boundary."""
    with pytest.raises(ValueError):
        SectorRotationSignal(
            sector=SectorIdentifier(sector_id="energy", name="Energy"),
            classification="outperform",
        )

