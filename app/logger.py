import logging

LOG_FORMAT = "[%(asctime)s.%(msecs)03d] [%(levelname)-4.4s] %(message)s [%(name)s] [%(filename)s:%(lineno)d]"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> dict[str, object]:
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    logging.captureWarnings(True)  # noqa: FBT003

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"default": {"fmt": LOG_FORMAT, "datefmt": DATE_FORMAT}},
        "handlers": {"default": {"class": "logging.StreamHandler", "formatter": "default"}},
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": [], "level": "WARNING", "propagate": False},
        },
    }
