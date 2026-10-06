"""CLI remporte — répondre à un appel d'offres publics avec votre agent IA."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("remporte")
except PackageNotFoundError:  # exécuté depuis les sources sans installation
    __version__ = "0.0.0"
