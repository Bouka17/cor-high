from dataclasses import dataclass


@dataclass(frozen=True)
class SegmentSpec:
    start: float
    end: float


@dataclass(frozen=True)
class ScoredSegment:
    start: float
    end: float
    motion_score: float
    audio_score: float
    total_score: float


@dataclass(frozen=True)
class SelectedSegment:
    start: float
    end: float
    score: float
