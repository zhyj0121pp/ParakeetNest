"""Tests for the portfolio committee CLI runner."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from parakeetnest.cli import portfolio_committee
from parakeetnest.committee import AgentResult, MeetingStatus
from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MeetingContext,
    PortfolioSnapshot,
)
from parakeetnest.portfolio.orchestrator import PortfolioCommitteeResult


def _result(account_id: str = "mock-main") -> PortfolioCommitteeResult:
    payload = {
        "agent_name": "Portfolio Manager",
        "role": "Portfolio Manager",
        "portfolio_view": "Portfolio was reviewed.",
        "advisory_action": "monitor",
        "confidence": "medium",
        "horizon": "3_months",
        "evidence": [
            {
                "summary": "Mock portfolio context.",
                "source": "test",
                "observed_at": None,
            }
        ],
        "risks": ["Concentration risk."],
        "catalysts": ["Earnings updates."],
    }
    return PortfolioCommitteeResult(
        status=MeetingStatus.COMPLETED,
        question=f"Review portfolio account {account_id}.",
        ticker="PORTFOLIO",
        agent_results=(
            AgentResult(
                agent_name="Portfolio Manager",
                role="Portfolio Manager",
                content=json.dumps(payload, sort_keys=True),
                agent_id="portfolio_manager",
                ticker="PORTFOLIO",
            ),
        ),
        metadata={
            "committee": "portfolio",
            "mode": "advisory_analytical",
            "non_execution": True,
        },
        portfolio_context=MeetingContext(
            request=ContextRequest(
                question=f"Review portfolio account {account_id}.",
                symbols=("PORTFOLIO",),
            ),
            metadata=ContextMetadata(sources=("portfolio",)),
            portfolio=PortfolioSnapshot(
                source="portfolio",
                account_id=account_id,
                total_equity=100000.0,
                cash_balance=2500.0,
                holding_count=2,
                symbols=("NVDA", "MSFT"),
            ),
        ),
    )


@dataclass
class RecordingOrchestrator:
    result: PortfolioCommitteeResult
    calls: list[tuple[str, str]]

    def run(self, question: str, *, ticker: str) -> PortfolioCommitteeResult:
        self.calls.append((question, ticker))
        return self.result


@dataclass
class RecordingRunner:
    orchestrator: RecordingOrchestrator
    closed: bool = False

    def close(self) -> None:
        self.closed = True


def test_cli_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        portfolio_committee.main(["--help"])

    output = capsys.readouterr().out
    assert exc.value.code == 0
    assert "--account-id" in output
    assert "--no-memory" in output
    assert "--verbose" in output


def test_default_mock_account_run_works_with_mocked_runtime(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, bool]] = []
    runner = RecordingRunner(RecordingOrchestrator(_result(), []))

    def create_runner(*, account_id, use_memory, database_path):
        calls.append((account_id, use_memory))
        assert database_path is None
        return runner

    monkeypatch.setattr(
        portfolio_committee,
        "create_portfolio_committee_runner",
        create_runner,
    )

    exit_code = portfolio_committee.main([])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == [("mock-main", True)]
    assert runner.closed is True
    assert runner.orchestrator.calls == [
        ("Review portfolio account mock-main.", "PORTFOLIO")
    ]
    assert "Portfolio Committee Meeting" in output
    assert "account_id: mock-main" in output
    assert "Portfolio Manager" in output


def test_account_id_option_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []

    def create_runner(*, account_id, use_memory, database_path):
        calls.append(account_id)
        return RecordingRunner(RecordingOrchestrator(_result(account_id), []))

    monkeypatch.setattr(
        portfolio_committee,
        "create_portfolio_committee_runner",
        create_runner,
    )

    exit_code = portfolio_committee.main(["--account-id", "mock-main"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == ["mock-main"]
    assert "account_id: mock-main" in output


def test_no_memory_option_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[bool] = []

    def create_runner(*, account_id, use_memory, database_path):
        calls.append(use_memory)
        return RecordingRunner(RecordingOrchestrator(_result(account_id), []))

    monkeypatch.setattr(
        portfolio_committee,
        "create_portfolio_committee_runner",
        create_runner,
    )

    exit_code = portfolio_committee.main(["--account-id", "mock-main", "--no-memory"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == [False]
    assert "memory_enabled: false" in output


def test_output_includes_metadata_and_advisory_only_language(
    capsys: pytest.CaptureFixture[str],
) -> None:
    portfolio_committee.print_portfolio_committee_result(
        _result(),
        account_id="mock-main",
        memory_enabled=True,
    )

    output = capsys.readouterr().out
    assert "Portfolio Committee Meeting" in output
    assert "committee: portfolio" in output
    assert "mode: advisory_analytical" in output
    assert "Advisory research only" in output
    assert "does not connect to brokerages" in output
    assert "execute trades" in output
    assert "automatic rebalancing" in output


def test_no_trade_execution_behavior_exists() -> None:
    runner = portfolio_committee.create_portfolio_committee_runner(
        account_id="mock-main",
        use_memory=False,
    )
    try:
        forbidden_attributes = (
            "execute_trade",
            "place_order",
            "submit_order",
            "rebalance",
            "robinhood",
            "brokerage_api",
        )
        for attribute in forbidden_attributes:
            assert not hasattr(portfolio_committee, attribute)
            assert not hasattr(runner.orchestrator, attribute)
            assert not hasattr(runner.orchestrator.agent_runtime, attribute)
    finally:
        runner.close()
