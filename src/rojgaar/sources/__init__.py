"""Source adapters. Each maps one job board or ATS into ``Job`` records."""

from .ashby import AshbySource
from .base import REGISTRY, FeedSource, Source, get_source
from .greenhouse import GreenhouseSource
from .hn import HNWhosHiringSource
from .lever import LeverSource
from .remoteok import RemoteOKSource
from .remotive import RemotiveSource

__all__ = [
    "REGISTRY",
    "AshbySource",
    "FeedSource",
    "GreenhouseSource",
    "HNWhosHiringSource",
    "LeverSource",
    "RemoteOKSource",
    "RemotiveSource",
    "Source",
    "get_source",
]
