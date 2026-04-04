import logging

log = logging.getLogger(__name__)


def test_nothing() -> None:
    log.info("This is a test")


def test_main_module_runs() -> None:
    from app import main  # noqa: PLC0415

    main.main()
