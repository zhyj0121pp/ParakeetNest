"""Tests for package dependency boundaries."""

import ast
from pathlib import Path


def test_data_collection_orchestrator_does_not_import_orm_models() -> None:
    """The orchestrator should delegate persistence instead of importing ORM models."""
    source_path = Path("src/parakeetnest/services/orchestrator.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)

    assert "parakeetnest.database.models" not in imported_modules
    assert all(not module.startswith("sqlalchemy") for module in imported_modules)


def test_bootstrap_dependency_direction_stays_out_of_services_agents_and_runtime() -> None:
    """Only the application bootstrap layer should depend on app.py."""
    source_paths = (
        Path("src/parakeetnest/services"),
        Path("src/parakeetnest/committee"),
        Path("src/parakeetnest/runtime.py"),
    )

    imported_modules = []
    for source_path in source_paths:
        paths = source_path.rglob("*.py") if source_path.is_dir() else (source_path,)
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module is not None:
                    imported_modules.append(node.module)
                elif isinstance(node, ast.Import):
                    imported_modules.extend(alias.name for alias in node.names)

    assert "parakeetnest.app" not in imported_modules


def test_meeting_service_has_no_market_data_dependency() -> None:
    """MeetingService must receive market data only through ContextService."""
    source_path = Path("src/parakeetnest/services/meeting.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)

    assert all(
        not module.startswith("parakeetnest.market_data")
        for module in imported_modules
    )
    assert all("MarketData" not in ast.unparse(node) for node in ast.walk(tree))


def test_meeting_service_has_no_sec_filing_dependency() -> None:
    """MeetingService must receive filings only through ContextService."""
    source_path = Path("src/parakeetnest/services/meeting.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)

    assert all(not module.startswith("parakeetnest.sec") for module in imported_modules)
    assert all("SecFiling" not in ast.unparse(node) for node in ast.walk(tree))


def test_committee_runtime_has_no_sec_filing_dependency() -> None:
    """Committee agents should consume filing context, not SEC provider services."""
    source_path = Path("src/parakeetnest/committee")

    imported_modules = []
    source = ""
    for path in source_path.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        source += text
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)
            elif isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)

    assert all(not module.startswith("parakeetnest.sec") for module in imported_modules)
    assert "SecFilingService" not in source


def test_committee_agents_do_not_depend_on_intelligence_source_services() -> None:
    """Committee agents should consume rendered context, not fetch source signals."""
    source_path = Path("src/parakeetnest/committee")
    forbidden_module_prefixes = (
        "parakeetnest.market_data",
        "parakeetnest.news",
        "parakeetnest.macro",
        "parakeetnest.intelligence.risk",
        "parakeetnest.intelligence.sentiment",
        "parakeetnest.intelligence.health",
        "parakeetnest.intelligence.momentum",
        "parakeetnest.intelligence.market_breadth",
        "parakeetnest.intelligence.sector_rotation",
    )
    forbidden_service_names = (
        "MarketDataService",
        "NewsService",
        "MacroDataService",
        "RiskService",
        "MarketSentimentService",
        "MarketHealthService",
        "MomentumService",
        "MarketBreadthService",
        "SectorRotationService",
    )

    imported_modules = []
    source = ""
    for path in source_path.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        source += text
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)
            elif isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)

    assert all(
        not module.startswith(forbidden_module_prefixes)
        for module in imported_modules
    )
    assert all(service_name not in source for service_name in forbidden_service_names)


def test_context_service_does_not_access_news_provider_registry() -> None:
    """ContextService must receive news through context providers and NewsService."""
    source_path = Path("src/parakeetnest/context/service.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported_modules = []
    source = source_path.read_text(encoding="utf-8")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)

    assert "parakeetnest.news.registry" not in imported_modules
    assert "NewsProviderRegistry" not in source


def test_yahoo_finance_code_stays_isolated_to_yahoo_provider() -> None:
    """Yahoo Finance dependencies should stay inside the Yahoo adapter."""
    source_paths = Path("src/parakeetnest").rglob("*.py")
    yahoo_provider_paths = {
        Path("src/parakeetnest/market_data/yahoo.py"),
        Path("src/parakeetnest/news/yahoo.py"),
    }

    for source_path in source_paths:
        if source_path in yahoo_provider_paths:
            continue
        source = source_path.read_text(encoding="utf-8").lower()
        assert "yfinance" not in source
        assert "yahoo finance" not in source


def test_robinhood_code_stays_isolated_to_robinhood_provider_and_registry() -> None:
    """Robinhood dependencies should stay out of committee and report logic."""
    allowed_paths = {
        Path("src/parakeetnest/config.py"),
        Path("src/parakeetnest/cli/doctor.py"),
        Path("src/parakeetnest/portfolio/robinhood.py"),
        Path("src/parakeetnest/portfolio/registry.py"),
    }

    for source_path in Path("src/parakeetnest").rglob("*.py"):
        if source_path in allowed_paths:
            continue
        source = source_path.read_text(encoding="utf-8").lower()
        assert "robin_stocks" not in source
        assert "robinhood" not in source
