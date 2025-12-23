"""Summarizers module for generating file summaries."""
from summarizers.base import BaseSummarizer
from summarizers.simple import SimpleSummarizer

# MinistralSummarizer available but optional due to dependencies
try:
    from summarizers.ministral import MinistralSummarizer
    __all__ = ["BaseSummarizer", "SimpleSummarizer", "MinistralSummarizer"]
except ImportError:
    MinistralSummarizer = None
    __all__ = ["BaseSummarizer", "SimpleSummarizer"]
