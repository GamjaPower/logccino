from .parser import LogParser

__all__ = ["LogParser"]

try:
    from .pipeline import IngestionPipeline
    __all__.append("IngestionPipeline")
except ImportError:
    pass

