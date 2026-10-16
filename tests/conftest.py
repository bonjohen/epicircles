"""Pytest / Hypothesis session configuration.

Registers and loads a derandomized Hypothesis profile so property-based tests
are deterministic (CLAUDE.md: no unseeded randomness; same input + environment
-> identical results). ``deadline=None`` avoids flaky timing failures on slow
CI or first-call JIT warmup.
"""
from hypothesis import settings

settings.register_profile("epicycles", derandomize=True, deadline=None)
settings.load_profile("epicycles")
