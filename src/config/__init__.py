"""Configuration package — centralized access to settings instances."""

from .browser import browser_settings
from .lcw import lcw_settings
from .ollama import ollama_settings
from .simroute import simroute_settings

__all__ = [
    "browser_settings",
    "ollama_settings",
    "lcw_settings",
    "simroute_settings",
]
