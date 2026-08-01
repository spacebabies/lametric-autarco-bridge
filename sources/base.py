"""Base data contracts for power generation sources."""
from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass
class GenerationReading:
    """
    Uniform data structure for inverter generation measurements.

    Attributes:
        power_watts: Current inverter output in Watts. Positive = producing.
        timestamp: ISO8601 timestamp string, optional.
    """
    power_watts: float
    timestamp: str | None = None


class GenerationSource(Protocol):
    """Protocol for ingress sources."""

    async def connect(self) -> None:
        """Initialize the connection to the generation source."""
        ...

    async def stream(self) -> AsyncIterator[GenerationReading]:
        """Stream generation readings as they arrive."""
        ...
