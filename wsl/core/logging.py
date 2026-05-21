"""Configuração de logging estruturado para o CelIA."""
from __future__ import annotations

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configura o logger raiz 'celia' com formato padronizado."""
    logger = logging.getLogger("celia")
    if logger.handlers:
        return
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Retorna logger filho do namespace 'celia'."""
    return logging.getLogger(f"celia.{name}")
