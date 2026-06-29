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
