from .types import ScoredSegment, SelectedSegment


def select_segments(
    scored_segments: list[ScoredSegment], target_duration_seconds: float
) -> list[SelectedSegment]:
    ranked = sorted(scored_segments, key=lambda seg: seg.total_score, reverse=True)
    selected: list[ScoredSegment] = []
    total = 0.0
    for segment in ranked:
        duration = segment.end - segment.start
        if total + duration <= target_duration_seconds:
            selected.append(segment)
            total += duration
        if total >= target_duration_seconds:
            break
    ordered = sorted(selected, key=lambda seg: seg.start)
    return [
        SelectedSegment(start=seg.start, end=seg.end, score=seg.total_score)
        for seg in ordered
    ]
