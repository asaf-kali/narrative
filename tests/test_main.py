import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import main
import pytest
from seed_data import SCHEMA_SQL, seed_msgstore
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def _mock_uvicorn_run() -> Iterator[mock.MagicMock]:
    with mock.patch.object(main.uvicorn, "run") as mocked:
        yield mocked


@pytest.fixture
def _mock_create_api() -> Iterator[mock.MagicMock]:
    with mock.patch("api.server.create_api") as mocked:
        yield mocked


@pytest.fixture
def _mock_semantic_index_fns() -> Iterator[tuple[mock.MagicMock, mock.MagicMock]]:
    with (
        mock.patch.object(main, "_run_index") as run_index,
        mock.patch.object(main, "_run_chat") as run_chat,
    ):
        yield run_index, run_chat


def _write_msgstore(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA_SQL)
    seed_msgstore(conn)
    conn.close()


def test_resolve_data_dir_auto_detects_files(tmp_path: Path) -> None:
    _write_msgstore(tmp_path / "msgstore.db")
    resolved = main._resolve_data_dir(data_dir=tmp_path, msgstore=None, wadb=None, contacts=None)
    assert resolved is not None
    assert resolved.msgstore == tmp_path / "msgstore.db"
    assert resolved.wadb is None
    assert resolved.contacts is None


def test_resolve_data_dir_finds_optional_files(tmp_path: Path) -> None:
    _write_msgstore(tmp_path / "msgstore.db")
    (tmp_path / "wa.db").touch()
    (tmp_path / "contacts.csv").touch()
    resolved = main._resolve_data_dir(data_dir=tmp_path, msgstore=None, wadb=None, contacts=None)
    assert resolved is not None
    assert resolved.wadb == tmp_path / "wa.db"
    assert resolved.contacts == tmp_path / "contacts.csv"


def test_resolve_data_dir_explicit_msgstore_takes_priority_over_data_dir(tmp_path: Path) -> None:
    # An explicit msgstore must win even when data_dir is also set (its CLI default is "data").
    explicit = tmp_path / "explicit_msgstore.db"
    resolved = main._resolve_data_dir(data_dir=Path("data"), msgstore=explicit, wadb=None, contacts=None)
    assert resolved is not None
    assert resolved.msgstore == explicit


def test_resolve_data_dir_none_when_nothing_given() -> None:
    assert main._resolve_data_dir(data_dir=None, msgstore=None, wadb=None, contacts=None) is None


# CLI tests drive via --data-dir <tmp> to isolate from the repo's real ./data directory,
# except where the explicit --msgstore priority is under test.


def test_serve_exits_1_when_msgstore_file_missing(tmp_path: Path) -> None:
    result = runner.invoke(main.cli, ["serve", "--data-dir", str(tmp_path)])  # empty dir, no msgstore.db
    assert result.exit_code == 1


def test_serve_starts_uvicorn_without_reload(
    tmp_path: Path, _mock_uvicorn_run: mock.MagicMock, _mock_create_api: mock.MagicMock
) -> None:
    _write_msgstore(tmp_path / "msgstore.db")
    result = runner.invoke(main.cli, ["serve", "--data-dir", str(tmp_path), "--port", "9999"])
    assert result.exit_code == 0
    _mock_uvicorn_run.assert_called_once()
    call_kwargs = _mock_uvicorn_run.call_args.kwargs
    assert call_kwargs["port"] == 9999


def test_serve_explicit_msgstore_wins_over_default_data_dir(
    tmp_path: Path, _mock_uvicorn_run: mock.MagicMock, _mock_create_api: mock.MagicMock
) -> None:
    # --msgstore is honoured even though --data-dir defaults to "data" (regression guard).
    msgstore = tmp_path / "custom.db"
    _write_msgstore(msgstore)
    result = runner.invoke(main.cli, ["serve", "--msgstore", str(msgstore)])
    assert result.exit_code == 0
    _mock_create_api.assert_called_once()
    assert _mock_create_api.call_args.kwargs["msgstore_path"] == msgstore


def test_serve_reload_mode_uses_import_string_and_env_vars(tmp_path: Path, _mock_uvicorn_run: mock.MagicMock) -> None:
    msgstore = tmp_path / "msgstore.db"
    _write_msgstore(msgstore)
    result = runner.invoke(main.cli, ["serve", "--data-dir", str(tmp_path), "--reload"])
    assert result.exit_code == 0
    args, kwargs = _mock_uvicorn_run.call_args
    assert args[0] == "api.asgi:app"
    assert kwargs["reload"] is True
    assert os.environ["WHATSAPP_MSGSTORE"] == str(msgstore)


def test_index_exits_1_when_msgstore_missing(tmp_path: Path) -> None:
    result = runner.invoke(main.cli, ["index", "--data-dir", str(tmp_path)])  # empty dir, no msgstore.db
    assert result.exit_code == 1


def test_index_exits_1_when_semantic_deps_missing_full_index(
    tmp_path: Path, _mock_semantic_index_fns: tuple[mock.MagicMock, mock.MagicMock]
) -> None:
    _write_msgstore(tmp_path / "msgstore.db")
    with mock.patch.object(main, "_run_index", None):
        result = runner.invoke(main.cli, ["index", "--data-dir", str(tmp_path)])
    assert result.exit_code == 1


def test_index_exits_1_when_semantic_deps_missing_chat_index(
    tmp_path: Path, _mock_semantic_index_fns: tuple[mock.MagicMock, mock.MagicMock]
) -> None:
    _write_msgstore(tmp_path / "msgstore.db")
    with mock.patch.object(main, "_run_chat", None):
        result = runner.invoke(main.cli, ["index", "--data-dir", str(tmp_path), "--chat-id", "1"])
    assert result.exit_code == 1


def test_index_full_calls_run_index(
    tmp_path: Path, _mock_semantic_index_fns: tuple[mock.MagicMock, mock.MagicMock]
) -> None:
    run_index, _ = _mock_semantic_index_fns
    _write_msgstore(tmp_path / "msgstore.db")
    result = runner.invoke(main.cli, ["index", "--data-dir", str(tmp_path)])
    assert result.exit_code == 0
    run_index.assert_called_once()


def test_index_chat_id_calls_run_chat(
    tmp_path: Path, _mock_semantic_index_fns: tuple[mock.MagicMock, mock.MagicMock]
) -> None:
    _run_index, run_chat = _mock_semantic_index_fns
    _write_msgstore(tmp_path / "msgstore.db")
    result = runner.invoke(main.cli, ["index", "--data-dir", str(tmp_path), "--chat-id", "1"])
    assert result.exit_code == 0
    run_chat.assert_called_once()
    assert run_chat.call_args.kwargs["chat_id"] == 1
