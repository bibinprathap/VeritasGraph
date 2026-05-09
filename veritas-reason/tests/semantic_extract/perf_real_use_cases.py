import statistics
import time
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from veritasreason.semantic_extract.event_detector import EventDetector
from veritasreason.semantic_extract.ner_extractor import NERExtractor
from veritasreason.semantic_extract.relation_extractor import RelationExtractor
from veritasreason.semantic_extract.semantic_analyzer import SemanticAnalyzer
from veritasreason.semantic_extract.semantic_network_extractor import SemanticNetworkExtractor
from veritasreason.semantic_extract.triplet_extractor import TripletExtractor
from veritasreason.utils.progress_tracker import get_progress_tracker


def _make_documents(n: int) -> List[Dict[str, str]]:
    base = (
        "Apple Inc. was founded by Steve Jobs in 1976 and is headquartered in Cupertino, California. "
        "Microsoft Corporation was founded by Bill Gates and Paul Allen in 1975. "
        "In 2014, Apple acquired Beats Electronics for $3 billion. "
        "In 2023, Google announced a partnership with OpenAI to improve search experiences."
    )
    return [{"id": f"doc_{i}", "content": f"{base} Document number {i}."} for i in range(n)]


def _median_seconds(fn, repeats: int = 3) -> float:
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def _bench(label: str, fn, repeats: int = 3) -> dict:
    fn()
    seconds = _median_seconds(fn, repeats=repeats)
    return {"label": label, "seconds": seconds}


def main():
    progress = get_progress_tracker()
    progress.displays = []

    docs = _make_documents(80)
    texts = [d["content"] for d in docs]

    ner = NERExtractor(method="pattern")
    rel = RelationExtractor(method="pattern")
    trip = TripletExtractor(method="pattern")
    events = EventDetector(method="pattern")
    analyzer = SemanticAnalyzer()
    net = SemanticNetworkExtractor(ner_method="pattern", relation_method="pattern")

    results = []

    def ner_parallel():
        ner.extract(texts)

    def ner_seq():
        ner.extract(texts, max_workers=1)

    results.append(_bench("NER batch (default workers)", ner_parallel))
    results.append(_bench("NER batch (max_workers=1)", ner_seq))

    entities_batch = ner.extract(texts)

    def rel_parallel():
        rel.extract(texts, entities_batch)

    def rel_seq():
        rel.extract(texts, entities_batch, max_workers=1)

    results.append(_bench("Relation batch (default workers)", rel_parallel))
    results.append(_bench("Relation batch (max_workers=1)", rel_seq))

    def trip_parallel():
        trip.extract(texts)

    def trip_seq():
        trip.extract(texts, max_workers=1)

    results.append(_bench("Triplet pipeline (default workers)", trip_parallel))
    results.append(_bench("Triplet pipeline (max_workers=1)", trip_seq))

    def ev_parallel():
        events.detect_events(texts)

    def ev_seq():
        events.detect_events(texts, max_workers=1)

    results.append(_bench("Event detection (default workers)", ev_parallel))
    results.append(_bench("Event detection (max_workers=1)", ev_seq))

    def analyzer_parallel():
        analyzer.analyze(texts)

    def analyzer_seq():
        analyzer.analyze(texts, max_workers=1)

    results.append(_bench("Semantic analysis (default workers)", analyzer_parallel))
    results.append(_bench("Semantic analysis (max_workers=1)", analyzer_seq))

    def net_parallel():
        net.extract_network(texts)

    def net_seq():
        net.extract_network(texts, max_workers=1)

    results.append(_bench("Semantic network (default workers)", net_parallel))
    results.append(_bench("Semantic network (max_workers=1)", net_seq))

    per_doc = []
    for row in results:
        per_doc.append({**row, "ms_per_doc": (row["seconds"] / len(texts)) * 1000.0})

    print(f"Documents: {len(texts)}")
    for row in per_doc:
        print(f"{row['label']}: {row['seconds']:.3f}s  ({row['ms_per_doc']:.2f} ms/doc)")


if __name__ == "__main__":
    main()
