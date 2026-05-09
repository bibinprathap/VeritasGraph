from datetime import datetime, timezone

from veritasreason.kg import BiTemporalFact, TemporalBound, TemporalGraphQuery
from veritasreason.reasoning import IntervalRelation, TemporalInterval, TemporalReasoningEngine


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def interval(start: str, end, label: str | None = None) -> TemporalInterval:
    return TemporalInterval(start=dt(start), end=TemporalBound.OPEN if end is TemporalBound.OPEN else dt(end), label=label)


class TestTemporalReasoningEngine:
    def setup_method(self):
        self.engine = TemporalReasoningEngine()

    def test_allen_relations_cover_all_thirteen_cases(self):
        base = interval("2024-01-03T00:00:00Z", "2024-01-05T00:00:00Z")
        cases = {
            IntervalRelation.BEFORE: interval("2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"),
            IntervalRelation.AFTER: interval("2024-01-06T00:00:00Z", "2024-01-07T00:00:00Z"),
            IntervalRelation.MEETS: interval("2024-01-02T00:00:00Z", "2024-01-03T00:00:00Z"),
            IntervalRelation.MET_BY: interval("2024-01-05T00:00:00Z", "2024-01-06T00:00:00Z"),
            IntervalRelation.OVERLAPS: interval("2024-01-01T00:00:00Z", "2024-01-04T00:00:00Z"),
            IntervalRelation.OVERLAPPED_BY: interval("2024-01-04T00:00:00Z", "2024-01-06T00:00:00Z"),
            IntervalRelation.STARTS: interval("2024-01-03T00:00:00Z", "2024-01-04T00:00:00Z"),
            IntervalRelation.STARTED_BY: interval("2024-01-03T00:00:00Z", "2024-01-06T00:00:00Z"),
            IntervalRelation.DURING: interval("2024-01-03T12:00:00Z", "2024-01-04T12:00:00Z"),
            IntervalRelation.CONTAINS: interval("2024-01-02T00:00:00Z", "2024-01-06T00:00:00Z"),
            IntervalRelation.FINISHES: interval("2024-01-04T00:00:00Z", "2024-01-05T00:00:00Z"),
            IntervalRelation.FINISHED_BY: interval("2024-01-02T00:00:00Z", "2024-01-05T00:00:00Z"),
            IntervalRelation.EQUALS: interval("2024-01-03T00:00:00Z", "2024-01-05T00:00:00Z"),
        }

        assert {self.engine.relation(candidate, base) for candidate in cases.values()} == set(cases.keys())
        for expected, candidate in cases.items():
            assert self.engine.relation(candidate, base) is expected

    def test_merge_intervals_and_active_at_open_bound(self):
        merged = self.engine.merge_intervals(
            [
                interval("2024-01-01T00:00:00Z", "2024-01-03T00:00:00Z", "A"),
                interval("2024-01-02T00:00:00Z", "2024-01-04T00:00:00Z", "B"),
                interval("2024-01-10T00:00:00Z", "2024-01-11T00:00:00Z", "C"),
            ]
        )

        assert len(merged) == 2
        assert merged[0].start == dt("2024-01-01T00:00:00Z")
        assert merged[0].end == dt("2024-01-04T00:00:00Z")
        assert self.engine.active_at(
            TemporalInterval(start=dt("2024-01-01T00:00:00Z"), end=TemporalBound.OPEN),
            "2026-01-01T00:00:00Z",
        )

    def test_gap_analysis_and_coverage_percentage(self):
        gaps = self.engine.gap_analysis(
            [
                interval("2020-01-01T00:00:00Z", "2021-01-01T00:00:00Z"),
                interval("2022-01-01T00:00:00Z", "2023-01-01T00:00:00Z"),
            ],
            "2020-01-01T00:00:00Z",
            "2023-01-01T00:00:00Z",
        )

        assert len(gaps) == 1
        assert gaps[0].start == dt("2021-01-01T00:00:00Z")
        assert gaps[0].end == dt("2022-01-01T00:00:00Z")
        assert self.engine.coverage_percentage(
            [interval("2020-01-01T00:00:00Z", "2023-01-01T00:00:00Z")],
            "2020-01-01T00:00:00Z",
            "2023-01-01T00:00:00Z",
        ) == 1.0

    def test_timeline_of_orders_events_and_handles_open_intervals(self):
        graph = {
            "entities": [{"id": "supplier-1", "valid_from": "2020-01-01T00:00:00Z", "valid_until": TemporalBound.OPEN}],
            "relationships": [
                {"id": "r1", "source": "supplier-1", "target": "cert", "type": "certified", "valid_from": "2021-01-01T00:00:00Z", "valid_until": "2022-01-01T00:00:00Z"},
                {"id": "r2", "source": "supplier-1", "target": "renewal", "type": "certified", "valid_from": "2023-01-01T00:00:00Z", "valid_until": TemporalBound.OPEN},
            ],
        }

        events = self.engine.timeline_of("supplier-1", graph)

        assert [event["change_type"] for event in events] == ["added", "added", "removed", "added"]
        assert events == sorted(events, key=lambda item: (item["timestamp"], item["change_type"]))

    def test_retroactive_coverage_classifies_affected_partial_and_unaffected(self):
        revision = BiTemporalFact(
            valid_from=dt("2021-01-01T00:00:00Z"),
            valid_until=dt("2023-01-01T00:00:00Z"),
            recorded_at=dt("2024-01-01T00:00:00Z"),
        )
        originals = [
            {"id": "affected", "valid_from": "2020-01-01T00:00:00Z", "valid_until": "2023-01-01T00:00:00Z"},
            {"id": "unaffected", "valid_from": "2019-01-01T00:00:00Z", "valid_until": "2020-01-01T00:00:00Z"},
            {"id": "partial", "valid_from": "2022-01-01T00:00:00Z", "valid_until": "2024-01-01T00:00:00Z"},
        ]

        result = self.engine.retroactive_coverage(revision, originals)

        assert [fact["id"] for fact in result["affected"]] == ["affected"]
        assert [fact["id"] for fact in result["unaffected"]] == ["unaffected"]
        assert [fact["id"] for fact in result["partial"]] == ["partial"]

    def test_normalization_is_idempotent_and_used_by_temporal_graph_query(self):
        month_point = self.engine.normalize_timestamp("2024-06-15T14:32:10Z", "month")
        assert month_point == dt("2024-06-01T00:00:00Z")

        normalized = self.engine.normalize_interval("2024-06-15T00:00:00Z", "2024-08-20T00:00:00Z", "month")
        assert normalized.start == dt("2024-06-01T00:00:00Z")
        assert normalized.end == dt("2024-08-31T23:59:59.999999Z")
        assert self.engine.normalize_interval(normalized.start, normalized.end, "month") == normalized

        query = TemporalGraphQuery(temporal_granularity="month")
        graph = {
            "relationships": [
                {"id": "jan", "source": "A", "target": "B", "type": "rel", "valid_from": "2024-01-10T00:00:00Z", "valid_until": "2024-01-20T00:00:00Z"},
                {"id": "feb", "source": "A", "target": "C", "type": "rel", "valid_from": "2024-02-05T00:00:00Z", "valid_until": "2024-02-10T00:00:00Z"},
            ]
        }

        result = query.query_time_range(graph, "", "2024-01-15T12:00:00Z", "2024-02-01T00:00:00Z")
        assert result["start_time"] == dt("2024-01-01T00:00:00Z")
        assert result["end_time"] == dt("2024-02-29T23:59:59.999999Z")
        assert {rel["id"] for rel in result["relationships"]} == {"jan", "feb"}

    def test_query_time_range_with_open_end_does_not_crash(self):
        query = TemporalGraphQuery(temporal_granularity="day")
        graph = {
            "relationships": [
                {"id": "open", "source": "A", "target": "B", "type": "rel", "valid_from": "2024-01-10T00:00:00Z", "valid_until": TemporalBound.OPEN},
            ]
        }

        result = query.query_time_range(graph, "", "2024-01-01T00:00:00Z", None)

        assert result["end_time"] is TemporalBound.OPEN
        assert [rel["id"] for rel in result["relationships"]] == ["open"]

    def test_query_at_time_respects_month_granularity(self):
        query = TemporalGraphQuery(temporal_granularity="month")
        graph = {
            "relationships": [
                {"id": "late-jan", "source": "A", "target": "B", "type": "rel", "valid_from": "2024-01-20T00:00:00Z", "valid_until": "2024-02-10T00:00:00Z"},
            ]
        }

        january = query.query_at_time(graph, "", "2024-01-05T00:00:00Z")
        february = query.query_at_time(graph, "", "2024-02-15T00:00:00Z")

        assert [rel["id"] for rel in january["relationships"]] == ["late-jan"]
        assert february["relationships"] == []
