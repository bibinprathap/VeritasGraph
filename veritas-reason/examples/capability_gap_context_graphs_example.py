"""
Capability Gap Analysis with VeritasReason Context Graphs

This example mirrors the military capability-gap notebook as a runnable Python script.
It uses VeritasReason modules and classes across ingestion, parsing, ontology handling,
splitting, normalization, semantic extraction, KG analytics, context graphs,
reasoning, provenance, and export.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from veritasreason.change_management import VersionManager
from veritasreason.conflicts import detect_conflicts, resolve_conflicts, voting
from veritasreason.context import (
    AgentContext,
    ContextGraph,
    Decision,
    Policy,
    PolicyEngine,
    multi_hop_query,
)
from veritasreason.export import (
    ReportGenerator,
    export_csv,
    export_graph,
    export_json,
    export_lpg,
    export_rdf,
    export_yaml,
)
from veritasreason.ingest import FileIngestor, OntologyIngestor, ingest_web
from veritasreason.kg import (
    CentralityCalculator,
    CommunityDetector,
    ConnectivityAnalyzer,
    EntityResolver,
    GraphAnalyzer,
    GraphBuilder,
    LinkPredictor,
    NodeEmbedder,
    SimilarityCalculator,
)
from veritasreason.normalize import (
    clean_text,
    detect_language,
    handle_encoding,
    normalize_text,
)
from veritasreason.ontology import OntologyEvaluator, ingest_ontology
from veritasreason.parse import (
    DOCLING_AVAILABLE,
    DocumentParser,
    DoclingParser,
    PDFParser,
    parse_document,
    parse_pdf,
)
from veritasreason.pipeline import PipelineBuilder
from veritasreason.provenance import ProvenanceManager
from veritasreason.reasoning import ExplanationGenerator, Reasoner
from veritasreason.semantic_extract import (
    CoreferenceResolver,
    EventDetector,
    ExtractionValidator,
    NamedEntityRecognizer,
    RelationExtractor,
    SemanticAnalyzer,
    SemanticNetworkExtractor,
    TripletExtractor,
)
from veritasreason.split import TextSplitter
from veritasreason.vector_store import VectorStore
from veritasreason.visualization import KGVisualizer


def build_paths() -> tuple[Path, Path, Path]:
    # Keep paths workspace-relative so the script is portable across machines.
    repo_root = Path(__file__).resolve().parents[1]
    use_case_dir = repo_root / "cookbook" / "use_cases" / "capability_gap_defense"
    data_dir = use_case_dir / "data"
    output_dir = use_case_dir / "outputs_py"
    output_dir.mkdir(parents=True, exist_ok=True)
    return data_dir, use_case_dir, output_dir


def main() -> None:
    # -------------------------------------------------------------------------
    # Workspace setup
    # -------------------------------------------------------------------------
    data_dir, use_case_dir, output_dir = build_paths()

    # -------------------------------------------------------------------------
    # 1) Ingestion (VeritasReason ingest)
    # -------------------------------------------------------------------------
    # Local file inventory for PDFs and ontology artifacts.
    file_ingestor = FileIngestor()
    file_objects = file_ingestor.ingest_directory(data_dir, recursive=False, read_content=False)

    # Web source ingestion through VeritasReason's `ingest_web` method wrapper.
    web_sources = [
        "https://www.rand.org/pubs/research_reports/RRA733-1.html",
        "https://foundationcapital.com/context-graphs/",
    ]
    web_contents = []
    for url in web_sources:
        try:
            web_contents.append(ingest_web(url, method="url"))
        except Exception as exc:
            print(f"Web ingestion failed for {url}: {exc}")

    # TTL ontology ingestion from the same data directory.
    ontology_ingestor = OntologyIngestor()
    ontology_data = ontology_ingestor.ingest_directory(data_dir, recursive=False)

    # -------------------------------------------------------------------------
    # 2) Ontology introspection + evaluation (VeritasReason ontology)
    # -------------------------------------------------------------------------
    # Capture file-level schema details to verify class/property coverage.
    ontology_details = []
    for ttl_file in sorted(data_dir.glob("*.ttl")):
        try:
            od = ingest_ontology(ttl_file, method="file")
            if isinstance(od, list):
                for item in od:
                    ontology_details.append(
                        {
                            "file": ttl_file.name,
                            "classes": len(item.data.get("classes", [])),
                            "properties": len(item.data.get("properties", [])),
                        }
                    )
            else:
                ontology_details.append(
                    {
                        "file": ttl_file.name,
                        "classes": len(od.data.get("classes", [])),
                        "properties": len(od.data.get("properties", [])),
                    }
                )
        except Exception as exc:
            ontology_details.append({"file": ttl_file.name, "error": str(exc)})

    # Run competency-question driven evaluation over one ontology payload.
    ontology_eval_result = None
    if ontology_data:
        evaluator = OntologyEvaluator()
        ontology_eval_result = evaluator.evaluate_ontology(
            ontology_data[0].data,
            competency_questions=[
                "What capability gaps are revealed for a mission thread?",
                "Which systems provide required capabilities?",
                "What evidence and provenance support a gap decision?",
                "Which precedents and exceptions affected a decision?",
            ],
        )

    # -------------------------------------------------------------------------
    # 3) Parsing (VeritasReason parse)
    # -------------------------------------------------------------------------
    # Parse PDFs through parse methods, with parser-class fallback.
    pdf_docs = []
    pdf_parser = PDFParser()
    doc_parser_preview = {}
    docling_preview = {"docling_available": bool(DOCLING_AVAILABLE)}

    for pdf_path in sorted(data_dir.glob("*.pdf")):
        try:
            # Primary parse path: module-level `parse_pdf`.
            parsed = parse_pdf(pdf_path, method="default", pages=list(range(0, 12)))
            if not isinstance(parsed, dict):
                # Fallback path: direct parser class call.
                parsed = pdf_parser.parse(pdf_path, pages=list(range(0, 12)))
            text = parsed.get("full_text", parsed.get("text", ""))
            if text:
                pdf_docs.append(
                    {
                        "doc_id": pdf_path.stem,
                        "source": str(pdf_path),
                        "text": text[:50000],
                        "metadata": parsed.get("metadata", {}),
                    }
                )
        except Exception as exc:
            print(f"PDF parse failed for {pdf_path.name}: {exc}")

    if pdf_docs:
        sample_pdf = Path(pdf_docs[0]["source"])
        try:
            # Generic multi-format parse via `parse_document`.
            parsed_doc = parse_document(sample_pdf, method="default")
            if not isinstance(parsed_doc, dict):
                parsed_doc = DocumentParser().parse_document(sample_pdf)
            doc_parser_preview = {
                "source": sample_pdf.name,
                "keys": list(parsed_doc.keys())[:10],
                "text_chars": len(parsed_doc.get("full_text", parsed_doc.get("text", "")) or ""),
            }
        except Exception as exc:
            doc_parser_preview = {"source": sample_pdf.name, "error": str(exc)}

        if docling_preview["docling_available"]:
            try:
                # Optional DoclingParser path when dependency is available.
                docling_parser = DoclingParser(export_format="markdown")
                dres = docling_parser.parse(sample_pdf)
                docling_preview["keys"] = list(dres.keys())[:10]
                docling_preview["text_chars"] = len(dres.get("full_text", dres.get("text", "")) or "")
            except Exception as exc:
                docling_preview["error"] = str(exc)

    # -------------------------------------------------------------------------
    # 4) Corpus assembly (input for split/normalize/extract)
    # -------------------------------------------------------------------------
    # Unify parsed PDFs, web documents, and ontology JSON snapshots.
    corpus = (
        [
            {"doc_id": d["doc_id"], "source": d["source"], "text": d["text"]}
            for d in pdf_docs
        ]
        + [
            {
                "doc_id": f"web_{i}",
                "source": getattr(w, "url", f"web_source_{i}"),
                "text": (getattr(w, "content", str(w)) or "")[:30000],
            }
            for i, w in enumerate(web_contents)
        ]
        + [
            {
                "doc_id": Path(od.source_path).stem,
                "source": od.source_path,
                "text": json.dumps(od.data, ensure_ascii=True)[:40000],
            }
            for od in ontology_data
        ]
    )

    # -------------------------------------------------------------------------
    # 5) Split + pipeline declaration (VeritasReason split + pipeline)
    # -------------------------------------------------------------------------
    # Batch splitting through `TextSplitter.split_batch`.
    splitter = TextSplitter(method="recursive", chunk_size=1800, chunk_overlap=250)
    chunks_by_doc = splitter.split_batch([doc.get("text", "") for doc in corpus])
    chunked_docs = []
    for doc, chunks in zip(corpus, chunks_by_doc):
        for idx, chunk in enumerate(chunks or []):
            chunked_docs.append(
                {
                    "doc_id": f"{doc['doc_id']}::chunk_{idx}",
                    "source": doc["source"],
                    "text": chunk.text if hasattr(chunk, "text") else str(chunk),
                    "parent_doc_id": doc["doc_id"],
                }
            )
    extraction_corpus = chunked_docs if chunked_docs else corpus

    # Logical orchestration path declared with VeritasReason PipelineBuilder.
    pipeline = (
        PipelineBuilder()
        .add_step("ingest_sources", "ingest", sources=len(corpus))
        .add_step("chunk_context", "split", method="recursive")
        .add_step("semantic_extract", "extract", entity_relation_event_triplet=True)
        .add_step("build_context_graph", "context_graph")
        .add_step("policy_and_trace", "decision_trace_capture")
        .add_step("export_and_observe", "export_observability")
        .connect_steps("ingest_sources", "chunk_context")
        .connect_steps("chunk_context", "semantic_extract")
        .connect_steps("semantic_extract", "build_context_graph")
        .connect_steps("build_context_graph", "policy_and_trace")
        .connect_steps("policy_and_trace", "export_and_observe")
        .build(name="capability_gap_orchestration_path")
    )

    # -------------------------------------------------------------------------
    # 6) Normalization (VeritasReason normalize)
    # -------------------------------------------------------------------------
    # Apply clean -> normalize -> detect_language -> handle_encoding.
    normalized_extraction_corpus = []
    for item in extraction_corpus:
        cleaned = clean_text(item.get("text", ""), method="default")
        normalized_text = normalize_text(cleaned, method="default") if cleaned else ""
        lang = detect_language(normalized_text, method="default") if normalized_text else "en"
        _ = handle_encoding(normalized_text, method="default") if normalized_text else normalized_text
        normalized_extraction_corpus.append({**item, "text": normalized_text, "language": lang})
    extraction_corpus = normalized_extraction_corpus

    # -------------------------------------------------------------------------
    # 7) Semantic extraction (VeritasReason semantic_extract)
    # -------------------------------------------------------------------------
    # Initialize VeritasReason extractors for entities, relations, events, triplets.
    ner = NamedEntityRecognizer(method="pattern", confidence_threshold=0.2)
    rel_extractor = RelationExtractor(method="pattern", confidence_threshold=0.2)
    evt_detector = EventDetector()
    coref = CoreferenceResolver()
    triplet_extractor = TripletExtractor(method="pattern", include_provenance=True)
    analyzer = SemanticAnalyzer()
    net_extractor = SemanticNetworkExtractor()
    validator = ExtractionValidator()

    # Resolve pronouns/coreferences before extraction to improve link quality.
    texts = [item.get("text", "") for item in extraction_corpus if item.get("text")]
    resolved_texts = [coref.resolve(t) for t in texts]

    # Batch-first extraction for entities/triplets; per-text for relations/events.
    entities_batch = ner.process_batch(resolved_texts)
    triplets_batch = triplet_extractor.process_batch(resolved_texts)
    relations_batch = [rel_extractor.extract_relations(t, entities=e) for t, e in zip(resolved_texts, entities_batch)]
    events_batch = [evt_detector.detect_events(t) for t in resolved_texts]

    all_entities = [e for batch in entities_batch for e in batch]
    all_relationships = [r for batch in relations_batch for r in batch]
    all_events = [ev for batch in events_batch for ev in batch]
    all_triplets = [tr for batch in triplets_batch for tr in batch]

    # Validation step keeps extraction quality checks explicit.
    _ = validator.validate_entities(all_entities)
    _ = validator.validate_relations(all_relationships)

    semantic_networks = [
        {
            "doc_id": extraction_corpus[i].get("doc_id", f"doc_{i}"),
            "analysis": analyzer.analyze(resolved_texts[i]),
            "network": net_extractor.extract(resolved_texts[i], entities=entities_batch[i], relations=relations_batch[i]),
        }
        for i in range(min(len(resolved_texts), len(extraction_corpus)))
    ]

    # -------------------------------------------------------------------------
    # 8) Quality controls + KG analytics (VeritasReason kg + conflicts)
    # -------------------------------------------------------------------------
    # Entity resolution for duplicate mentions.
    resolver = EntityResolver(strategy="fuzzy")
    entity_dicts = [
        {
            "id": str(getattr(e, "id", getattr(e, "text", "unknown"))),
            "name": str(getattr(e, "text", getattr(e, "id", "unknown"))),
            "type": str(getattr(e, "label", getattr(e, "type", "entity"))),
            "metadata": getattr(e, "metadata", {}) or {},
        }
        for e in all_entities
    ]
    resolved_entities = resolver.resolve_entities(entity_dicts[:200]) if entity_dicts else []

    # Conflict detection and resolution on contradictory numeric evidence.
    conflicts = detect_conflicts(
        [
            {"id": "System_GroundRadarLayer", "coveragePercent": "42", "type": "system"},
            {"id": "System_GroundRadarLayer", "coveragePercent": "58", "type": "system"},
        ],
        method="value",
        property_name="coveragePercent",
    )
    resolved_conflicts = resolve_conflicts(conflicts, method=voting) if conflicts else []

    # Build the knowledge graph from extracted entities/relationships.
    builder = GraphBuilder(merge_entities=True, resolve_conflicts=True)
    kg = builder.build([{"entities": all_entities, "relationships": all_relationships}], extract=False)

    analyzer_kg = GraphAnalyzer()
    kg_analysis = analyzer_kg.analyze_graph(kg)

    # Graph analytics modules: centrality, communities, connectivity, similarity.
    centrality_calc = CentralityCalculator()
    community_detector = CommunityDetector()
    connectivity_analyzer = ConnectivityAnalyzer()
    similarity_calc = SimilarityCalculator(method="cosine")
    link_predictor = LinkPredictor()
    node_embed_status = {}
    try:
        _ = NodeEmbedder(method="node2vec", embedding_dimension=32, walk_length=20, num_walks=5)
        node_embed_status["node2vec_ready"] = True
    except Exception as exc:
        node_embed_status = {"node2vec_ready": False, "reason": str(exc)}

    extended_kg_analytics = {
        "centrality": centrality_calc.calculate_all_centrality(kg),
        "communities": community_detector.detect_communities(kg, algorithm="louvain"),
        "connectivity": connectivity_analyzer.analyze_connectivity(kg),
        "sample_cosine_similarity": similarity_calc.cosine_similarity([1.0, 0.0, 1.0], [0.8, 0.2, 0.9]),
        "predicted_links": link_predictor.predict_links(kg, top_k=5),
        "node_embedding_status": node_embed_status,
    }

    # -------------------------------------------------------------------------
    # 9) Context graph + decision traces (VeritasReason context)
    # -------------------------------------------------------------------------
    # Domain skeleton nodes/edges for scenario -> mission -> event -> gap chain.
    context_graph = ContextGraph(advanced_analytics=True, centrality_analysis=True, community_detection=True)
    context_graph.add_nodes(
        [
            {"id": "Scenario_FutureA2AD_2028", "type": "scenario", "properties": {"content": "Future A2/AD escalation scenario"}},
            {"id": "MissionThread_ForceProtection", "type": "mission_thread", "properties": {"content": "Protect forward operating assets under drone saturation"}},
            {"id": "Event_LowAltitudeSwarmIncursions", "type": "event", "properties": {"content": "Repeated low-altitude swarm incursions"}},
            {"id": "System_GroundRadarLayer", "type": "system", "properties": {"content": "Ground radar surveillance layer"}},
            {"id": "Capability_LowAltitudeDetection", "type": "capability", "properties": {"content": "Low altitude detection capability"}},
            {"id": "Outcome_MissionRiskIncrease", "type": "outcome", "properties": {"content": "Rising mission risk and delayed response"}},
            {"id": "Gap_LowAltitudeDetectionCoverage", "type": "capability_gap", "properties": {"content": "Insufficient low-altitude detection coverage"}},
        ]
    )
    context_graph.add_edges(
        [
            {"source_id": "Scenario_FutureA2AD_2028", "target_id": "MissionThread_ForceProtection", "type": "has_mission_thread"},
            {"source_id": "MissionThread_ForceProtection", "target_id": "Event_LowAltitudeSwarmIncursions", "type": "includes_event"},
            {"source_id": "Event_LowAltitudeSwarmIncursions", "target_id": "System_GroundRadarLayer", "type": "stresses_system"},
            {"source_id": "System_GroundRadarLayer", "target_id": "Capability_LowAltitudeDetection", "type": "provides_capability"},
            {"source_id": "Capability_LowAltitudeDetection", "target_id": "Outcome_MissionRiskIncrease", "type": "affects_outcome"},
            {"source_id": "MissionThread_ForceProtection", "target_id": "Gap_LowAltitudeDetectionCoverage", "type": "reveals_gap"},
        ]
    )

    # AgentContext binds vector retrieval + context graph decision tracking.
    vector_store = VectorStore(backend="inmemory", dimension=384)
    agent_context = AgentContext(
        vector_store=vector_store,
        knowledge_graph=context_graph,
        decision_tracking=True,
        advanced_analytics=True,
        kg_algorithms=True,
        vector_store_features=True,
        graph_expansion=True,
        max_expansion_hops=3,
    )

    _ = agent_context.store(
        [{"content": c["text"][:2500], "metadata": {"source": c["source"], "doc_id": c["doc_id"]}} for c in corpus],
        extract_entities=False,
        extract_relationships=False,
    )

    # Example decision record for capability-gap assessment.
    decision_a = agent_context.record_decision(
        category="capability_gap_assessment",
        scenario="Future A2/AD mission thread with low-altitude swarm pressure",
        reasoning="Mission requires persistent low-altitude detection, but current radar layer indicates limited valley and urban coverage.",
        outcome="gap_identified_low_altitude_detection",
        confidence=0.93,
        entities=["MissionThread_ForceProtection", "Capability_LowAltitudeDetection", "Gap_LowAltitudeDetectionCoverage"],
    )

    # Explicit policy-bound trace decision object.
    trace_decision = Decision(
        decision_id="",
        category="capability_gap_assessment",
        scenario="Coverage threshold breach during swarm-pressure mission thread",
        reasoning="Below-threshold low-altitude detection coverage with repeated threat ingress; escalation required.",
        outcome="escalate_for_exception",
        confidence=0.89,
        timestamp=datetime.now(),
        decision_maker="joint_ops_agent",
        metadata={"policy_version": "3.2"},
    )

    # Policy and compliance checks against decision trace.
    policy_engine = PolicyEngine(context_graph)
    policy = Policy(
        policy_id="POL-CAPGAP-3.2",
        name="Capability Gap Escalation Policy",
        description="Escalate and require approval when mission-critical capability coverage is below threshold.",
        rules={
            "min_confidence": 0.8,
            "required_categories": ["capability_gap_assessment", "capability_gap_mitigation"],
            "allowed_outcomes": [
                "gap_identified_low_altitude_detection",
                "recommend_multilayer_sensor_fusion",
                "escalate_for_exception",
            ],
        },
        category="capability_gap_assessment",
        version="3.2",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={"entities": ["MissionThread_ForceProtection", "System_GroundRadarLayer"]},
    )
    policy_engine.add_policy(policy)
    trace_decision_id = context_graph.record_decision(
        category=trace_decision.category,
        scenario=trace_decision.scenario,
        reasoning=trace_decision.reasoning,
        outcome=trace_decision.outcome,
        confidence=trace_decision.confidence,
        entities=["MissionThread_ForceProtection", "Gap_LowAltitudeDetectionCoverage"],
        decision_maker=trace_decision.decision_maker,
        metadata={
            "policy_version": "3.2",
            "cross_system_context": {"crm": "critical_account", "zendesk": "open_escalation", "pagerduty": "sev1_incidents"},
        },
    )

    # Retrieve precedents and run multi-hop traversal in the context graph.
    _ = policy_engine.check_compliance(trace_decision, "POL-CAPGAP-3.2")
    _ = agent_context.find_precedents(
        scenario="Low-altitude detection shortfall under swarm pressure",
        category="capability_gap_assessment",
        limit=5,
        use_hybrid_search=True,
    )
    _ = context_graph.analyze_decision_impact(trace_decision_id)
    _ = multi_hop_query(
        context_graph,
        start_entity="Scenario_FutureA2AD_2028",
        query="Trace mission-thread to capability-gap path",
        max_hops=3,
    )

    # -------------------------------------------------------------------------
    # 10) Rule-based reasoning (VeritasReason reasoning)
    # -------------------------------------------------------------------------
    reasoner = Reasoner()
    reasoner.add_rule("IF MissionRequires(?m, LowAltitudeDetection) AND CoverageStatus(?m, Insufficient) THEN CapabilityGap(?m, LowAltitudeDetectionGap)")
    reasoner.add_rule("IF CapabilityGap(?m, LowAltitudeDetectionGap) AND ThreatLevel(?m, High) THEN OutcomeRisk(?m, Elevated)")
    reasoner.add_fact("MissionRequires(MissionThread_ForceProtection, LowAltitudeDetection)")
    reasoner.add_fact("CoverageStatus(MissionThread_ForceProtection, Insufficient)")
    reasoner.add_fact("ThreatLevel(MissionThread_ForceProtection, High)")
    inferred = reasoner.forward_chain()
    explanation_text = ""
    if inferred:
        explanation = ExplanationGenerator().generate_explanation(inferred[-1])
        explanation_text = explanation.natural_language

    # -------------------------------------------------------------------------
    # 11) Versioning + provenance (VeritasReason change_management + provenance)
    # -------------------------------------------------------------------------
    # Version policies/ontology structure and store lineage records.
    version_manager = VersionManager(base_uri="https://example.org/mcg")
    _ = version_manager.create_version(
        "3.1",
        ontology={"uri": "https://example.org/mcg", "classes": [], "properties": []},
        changes=["Initial capability-gap decision policy baseline"],
        metadata={"structure": {"classes": ["Scenario", "MissionThread", "CapabilityGap"], "properties": ["revealsGap"]}},
    )
    _ = version_manager.create_version(
        "3.2",
        ontology={"uri": "https://example.org/mcg", "classes": [], "properties": []},
        changes=["Added explicit policy exception and approval-chain trace constructs"],
        metadata={
            "structure": {
                "classes": ["Scenario", "MissionThread", "CapabilityGap", "PolicyException", "ApprovalChain"],
                "properties": ["revealsGap", "has_exception", "approved_by_chain"],
            }
        },
    )

    prov = ProvenanceManager(storage_path=str(output_dir / "capability_gap_provenance.db"))
    for c in corpus:
        prov.track_entity(entity_id=f"source::{c['doc_id']}", source=c["source"], metadata={"document_type": "corpus_source"})
    for i, rel in enumerate(all_relationships[:120]):
        prov.track_relationship(
            relationship_id=f"rel::{i}",
            source=(getattr(rel, "metadata", {}) or {}).get("source_doc", "unknown_source"),
            metadata={"relation_type": str(getattr(rel, "predicate", getattr(rel, "type", "related_to")))},
        )

    # -------------------------------------------------------------------------
    # 12) Export + visualization (VeritasReason export + visualization)
    # -------------------------------------------------------------------------
    # Export graph/context in multiple formats for downstream tools.
    export_json(kg, output_dir / "capability_gap_kg.json", format="json")
    export_json(context_graph.to_dict(), output_dir / "capability_gap_context_graph.json", format="json")
    export_graph(context_graph.to_dict(), output_dir / "capability_gap_context_graph.graphml", format="graphml")
    export_rdf(kg, output_dir / "capability_gap_kg.ttl", format="turtle")
    export_csv({"entities": kg.get("entities", []), "relationships": kg.get("relationships", [])}, output_dir / "capability_gap_kg")
    export_yaml(context_graph.to_dict(), output_dir / "capability_gap_context_graph.yaml")
    export_lpg(kg, output_dir / "capability_gap_kg.cypher", method="cypher")

    report_data = {
        "title": "Military Capability Gap Analysis - End-to-End Report",
        "summary": {
            "corpus_items": len(corpus),
            "extraction_items": len(extraction_corpus),
            "entities": len(all_entities),
            "relationships": len(all_relationships),
            "decisions": context_graph.get_decision_summary().get("total_decisions", 0),
        },
        "metrics": {
            "kg_entities": len(kg.get("entities", [])),
            "kg_relationships": len(kg.get("relationships", [])),
            "context_nodes": context_graph.stats().get("node_count", 0),
            "context_edges": context_graph.stats().get("edge_count", 0),
        },
        "analysis": {"kg_analysis": kg_analysis},
    }
    ReportGenerator(format="markdown", include_charts=False).generate_report(
        report_data,
        output_dir / "capability_gap_analysis_report.md",
        format="markdown",
    )

    # Optional network HTML visualization.
    try:
        KGVisualizer(layout="force", color_scheme="default").visualize_network(
            kg,
            output="html",
            file_path=output_dir / "capability_gap_kg_network.html",
        )
    except Exception as exc:
        print(f"Visualization skipped: {exc}")

    # Final run summary for quick validation.
    summary = {
        "use_case_dir": str(use_case_dir),
        "output_dir": str(output_dir),
        "files_ingested": len(file_objects),
        "web_docs_ingested": len(web_contents),
        "ontologies_ingested": len(ontology_data),
        "ontology_details": ontology_details,
        "ontology_eval": {
            "coverage_score": getattr(ontology_eval_result, "coverage_score", None),
            "completeness_score": getattr(ontology_eval_result, "completeness_score", None),
        },
        "doc_parser_preview": doc_parser_preview,
        "docling_preview": docling_preview,
        "pipeline": pipeline.name,
        "entities_extracted": len(all_entities),
        "relationships_extracted": len(all_relationships),
        "events_detected": len(all_events),
        "triplets_extracted": len(all_triplets),
        "semantic_networks": len(semantic_networks),
        "resolved_entities": len(resolved_entities),
        "conflicts_detected": len(conflicts),
        "conflicts_resolved": len(resolved_conflicts),
        "reasoning_inferred_rules": [r.conclusion for r in inferred],
        "reasoning_explanation": explanation_text,
        "extended_kg_analytics_keys": list(extended_kg_analytics.keys()),
        "provenance_stats": prov.get_statistics(),
        "decision_example": decision_a,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()

