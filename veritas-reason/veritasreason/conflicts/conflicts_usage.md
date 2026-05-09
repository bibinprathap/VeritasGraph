# Conflicts Module Usage Guide

This guide demonstrates how to use the conflicts module for detecting, resolving, and analyzing conflicts in knowledge graphs from multiple sources.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Conflict Detection](#conflict-detection)
3. [Conflict Resolution](#conflict-resolution)
4. [Conflict Analysis](#conflict-analysis)
5. [Source Tracking](#source-tracking)
6. [Investigation Guides](#investigation-guides)
7. [Using Methods](#using-methods)
8. [Using Registry](#using-registry)
9. [Configuration](#configuration)
10. [Advanced Examples](#advanced-examples)

## Basic Usage

### Using Main Classes

```python
from veritasreason.conflicts import ConflictDetector, ConflictResolver

# Step 1: Detect conflicts
detector = ConflictDetector(
    confidence_threshold=0.7,
    track_provenance=True
)

conflicts = detector.detect_value_conflicts(entities, "name")
print(f"Found {len(conflicts)} conflicts")

# Step 2: Resolve conflicts
resolver = ConflictResolver(
    default_strategy="voting"
)

results = resolver.resolve_conflicts(conflicts)
for result in results:
    if result.resolved:
        print(f"Resolved: {result.resolved_value} (confidence: {result.confidence:.2f})")
```

## Conflict Detection

### Value Conflict Detection

```python
from veritasreason.conflicts import ConflictDetector

detector = ConflictDetector()

# Detect conflicts in a specific property
conflicts = detector.detect_value_conflicts(
    entities,
    property_name="name",
    entity_type="Company"
)

for conflict in conflicts:
    print(f"Conflict ID: {conflict.conflict_id}")
    print(f"Property: {conflict.property_name}")
    print(f"Conflicting values: {conflict.conflicting_values}")
    print(f"Severity: {conflict.severity}")
    print(f"Confidence: {conflict.confidence:.2f}")
```

### Type Conflict Detection

```python
from veritasreason.conflicts import ConflictDetector

detector = ConflictDetector()

# Detect entity type conflicts
conflicts = detector.detect_type_conflicts(entities)

for conflict in conflicts:
    print(f"Entity {conflict.entity_id} has conflicting types")
    print(f"Conflicting types: {conflict.conflicting_values}")
```

### Relationship Conflict Detection

```python
from veritasreason.conflicts import ConflictDetector

detector = ConflictDetector()

# Sample relationships
relationships = [
    {"id": "rel1", "source_id": "1", "target_id": "2", "type": "competes_with"},
    {"id": "rel1", "source_id": "1", "target_id": "2", "type": "partners_with"},
]

# Detect relationship conflicts
conflicts = detector.detect_relationship_conflicts(relationships)

for conflict in conflicts:
    print(f"Relationship {conflict.relationship_id} has conflicts")
    print(f"Conflicting properties: {conflict.property_name}")
```

### Temporal Conflict Detection

```python
from veritasreason.conflicts import ConflictDetector

detector = ConflictDetector()

# Detect temporal conflicts (e.g., founded year conflicts)
conflicts = detector.detect_temporal_conflicts(entities)

for conflict in conflicts:
    print(f"Temporal conflict in {conflict.property_name}")
    print(f"Conflicting values: {conflict.conflicting_values}")
```

### Entity-Wide Conflict Detection

```python
from veritasreason.conflicts import ConflictDetector

detector = ConflictDetector(
    conflict_fields={
        "Company": ["name", "founded", "revenue", "headquarters"]
    }
)

# Detect all conflicts for entities
conflicts = detector.detect_entity_conflicts(
    entities,
    entity_type="Company"
)

print(f"Found {len(conflicts)} total conflicts across all properties")
```

### Integrated Detection and Basic Resolution

The `ConflictDetector` also provides a convenience method `resolve_conflicts` for basic resolution, which is primarily used by the `GraphBuilder`. For more control, use the `ConflictResolver` class.

```python
# Detect and automatically resolve conflicts (convenience method)
resolution_result = detector.resolve_conflicts(conflicts)
print(f"Resolved {resolution_result.get('resolved_count')} conflicts")
```

### Using Detection Methods

```python
from veritasreason.conflicts import ConflictDetector

detector = ConflictDetector()

value_conflicts = detector.detect_value_conflicts(entities, property_name="name")
type_conflicts = detector.detect_type_conflicts(entities)
relationship_conflicts = detector.detect_relationship_conflicts(relationships)
temporal_conflicts = detector.detect_temporal_conflicts(entities)

conflicts = (
    value_conflicts
    + type_conflicts
    + relationship_conflicts
    + temporal_conflicts
)
```

## Conflict Resolution

### Voting Strategy

```python
from veritasreason.conflicts import ConflictResolver

resolver = ConflictResolver()

# Resolve using voting (majority wins)
results = resolver.resolve_conflicts(
    conflicts,
    strategy="voting"
)

for result in results:
    if result.resolved:
        print(f"Resolved to: {result.resolved_value}")
        print(f"Sources used: {result.sources_used}")
```

### Credibility Weighted Strategy

```python
from veritasreason.conflicts import ConflictResolver

resolver = ConflictResolver()

# Resolve using credibility-weighted voting
results = resolver.resolve_conflicts(
    conflicts,
    strategy="credibility_weighted"
)

for result in results:
    if result.resolved:
        print(f"Resolved to: {result.resolved_value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Resolution notes: {result.resolution_notes}")
```

### Most Recent Strategy

```python
from veritasreason.conflicts import ConflictResolver

resolver = ConflictResolver()

# Resolve using most recent value
results = resolver.resolve_conflicts(
    conflicts,
    strategy="most_recent"
)

for result in results:
    if result.resolved:
        print(f"Resolved to most recent: {result.resolved_value}")
```

### Highest Confidence Strategy

```python
from veritasreason.conflicts import ConflictResolver

resolver = ConflictResolver()

# Resolve using highest confidence source
results = resolver.resolve_conflicts(
    conflicts,
    strategy="highest_confidence"
)

for result in results:
    if result.resolved:
        print(f"Resolved to highest confidence: {result.resolved_value}")
        print(f"Confidence: {result.confidence:.2f}")
```

### Manual Review Strategy

```python
from veritasreason.conflicts import ConflictResolver

resolver = ConflictResolver()

# Flag conflicts for manual review
results = resolver.resolve_conflicts(
    conflicts,
    strategy="manual_review"
)

for result in results:
    if not result.resolved:
        print(f"Conflict {result.conflict_id} flagged for manual review")
```

### Using Resolution Methods

```python
from veritasreason.conflicts import ConflictResolver

resolver = ConflictResolver()
results = resolver.resolve_conflicts(conflicts, strategy="voting")
```

## Conflict Analysis

### Pattern Analysis

```python
from veritasreason.conflicts import ConflictAnalyzer

analyzer = ConflictAnalyzer()

# Analyze conflict patterns
analysis = analyzer.analyze_conflicts(conflicts)

print(f"Total conflicts: {analysis['total_conflicts']}")
print(f"Patterns found: {len(analysis['patterns'])}")

for pattern in analysis['patterns']:
    print(f"Pattern: {pattern.pattern_type}, Frequency: {pattern.frequency}")
    print(f"Affected entities: {pattern.affected_entities}")
```

### Type Classification

```python
from veritasreason.conflicts import ConflictAnalyzer

analyzer = ConflictAnalyzer()

# Analyze by conflict type
analysis = analyzer.analyze_conflicts(conflicts)

print("Conflicts by type:")
for conflict_type, count in analysis['by_type']['counts'].items():
    print(f"  {conflict_type}: {count}")
```

### Severity Analysis

```python
from veritasreason.conflicts import ConflictAnalyzer

analyzer = ConflictAnalyzer()

# Analyze by severity
analysis = analyzer.analyze_conflicts(conflicts)

print("Conflicts by severity:")
for severity, count in analysis['by_severity']['counts'].items():
    print(f"  {severity}: {count} conflicts")
```

### Source Analysis

```python
from veritasreason.conflicts import ConflictAnalyzer

analyzer = ConflictAnalyzer()

# Analyze by source
analysis = analyzer.analyze_conflicts(conflicts)

print("Conflicts by source:")
for source, count in analysis['by_source']['counts'].items():
    print(f"  {source}: {count} conflicts")
```

### Trend Analysis

```python
from veritasreason.conflicts import ConflictAnalyzer

analyzer = ConflictAnalyzer()

# Analyze trends over time
trends = analyzer.analyze_trends(conflicts)

print("Conflict trends:")
for trend in trends:
    print(f"  {trend['period']}: {trend['conflict_count']} conflicts")
    print(f"  Trend: {trend['trend']}")
```

### Using Analysis Methods

```python
from veritasreason.conflicts import ConflictAnalyzer

analyzer = ConflictAnalyzer()
analysis = analyzer.analyze_conflicts(conflicts)
```

## Source Tracking

### Property Source Tracking

```python
from veritasreason.conflicts import SourceTracker, SourceReference
from datetime import datetime

tracker = SourceTracker()

# Create source reference
source = SourceReference(
    document="doc1",
    page=1,
    section="Company Overview",
    line=10,
    timestamp=datetime.now(),
    confidence=0.9
)

# Track property source
tracker.track_property_source(
    entity_id="entity_1",
    property_name="name",
    value="Apple Inc.",
    source=source
)

# Get property sources
prop_source = tracker.get_property_sources("entity_1", "name")
if prop_source:
    print(f"Value: {prop_source.value}")
    print(f"Sources: {len(prop_source.sources)}")
```

### Entity Source Tracking

```python
from veritasreason.conflicts import SourceTracker, SourceReference

tracker = SourceTracker()

# Track entity source
source = SourceReference(document="doc1", confidence=0.9)
tracker.track_entity_source("entity_1", source)

# Get entity sources
sources = tracker.get_entity_sources("entity_1")
print(f"Entity has {len(sources)} sources")
```

### Relationship Source Tracking

```python
from veritasreason.conflicts import SourceTracker, SourceReference

tracker = SourceTracker()

# Track relationship source
source = SourceReference(document="doc1", confidence=0.9)
tracker.track_relationship_source("rel_1", source)

# Get relationship sources
sources = tracker.get_relationship_sources("rel_1")
print(f"Relationship has {len(sources)} sources")
```

### Source Credibility

```python
from veritasreason.conflicts import SourceTracker

tracker = SourceTracker()

# Set source credibility
tracker.set_source_credibility("doc1", 0.9)
tracker.set_source_credibility("doc2", 0.7)

# Get source credibility
credibility = tracker.get_source_credibility("doc1")
print(f"Source credibility: {credibility:.2f}")

# Get all source credibilities
all_credibilities = tracker.get_all_source_credibilities()
for source, cred in all_credibilities.items():
    print(f"{source}: {cred:.2f}")
```

### Traceability Chain

```python
from veritasreason.conflicts import SourceTracker

tracker = SourceTracker()

# Generate traceability chain
chain = tracker.generate_traceability_chain("entity_1", "name")

print("Traceability chain:")
for step in chain:
    print(f"  {step['type']}: {step['entity_id']}.{step.get('property_name')}")
    print(f"    Source: {step.get('source', {}).get('document')}")
```

### Using Tracking Methods

```python
from veritasreason.conflicts import SourceTracker, SourceReference

source = SourceReference(document="doc1", confidence=0.9)
tracker = SourceTracker()
tracker.track_property_source("entity_1", "name", "Apple Inc.", source)

tracker.track_entity_source("entity_1", source)

tracker.track_relationship_source("rel_1", source)
```

## Investigation Guides

### Generate Investigation Guide

```python
from veritasreason.conflicts import InvestigationGuideGenerator

generator = InvestigationGuideGenerator()

# Generate guide for a conflict
guide = generator.generate_guide(conflict)

print(f"Conflict ID: {guide.conflict_id}")
print(f"Severity: {guide.severity}")
print(f"Summary: {guide.conflict_summary}")
print(f"Investigation steps: {len(guide.investigation_steps)}")

for step in guide.investigation_steps:
    print(f"  Step {step.step_number}: {step.description}")
    print(f"    Action: {step.action}")
```

### Generate Multiple Guides

```python
from veritasreason.conflicts import InvestigationGuideGenerator

generator = InvestigationGuideGenerator()

# Generate guides for multiple conflicts
guides = generator.generate_guides(conflicts)

for guide in guides:
    print(f"\nGuide for conflict {guide.conflict_id}:")
    print(f"  Steps: {len(guide.investigation_steps)}")
    print(f"  Recommended actions: {len(guide.recommended_actions)}")
```

### Export Investigation Checklist

```python
from veritasreason.conflicts import InvestigationGuideGenerator

generator = InvestigationGuideGenerator()

# Generate guide
guide = generator.generate_guide(conflict)

# Export as text
checklist_text = generator.export_investigation_checklist(guide, format="text")
print(checklist_text)

# Export as markdown
checklist_md = generator.export_investigation_checklist(guide, format="markdown")
print(checklist_md)
```

### Using Investigation Methods

```python
from veritasreason.conflicts import InvestigationGuideGenerator

generator = InvestigationGuideGenerator()
guide = generator.generate_guide(conflict)

checklist = generator.export_investigation_checklist(guide, format="text")

context = guide.context
```

## Using Methods

### List Available Methods

```python
from veritasreason.conflicts import MethodRegistry

# List all available methods
all_methods = MethodRegistry.list_all()
print("Registered methods:")
for task, methods in all_methods.items():
    print(f"  {task}: {methods}")

# List methods for specific task
detection_methods = MethodRegistry.list_all("detection")
print(f"Detection methods: {detection_methods}")
```

### Get Conflict Method

```python
from veritasreason.conflicts import MethodRegistry, ResolutionResult

def custom_resolution_method(conflicts, **kwargs):
    results = []
    for conflict in conflicts:
        result = ResolutionResult(
            conflict_id=conflict.conflict_id,
            resolved=True,
            resolved_value="custom_value"
        )
        results.append(result)
    return results

MethodRegistry.register("resolution", "custom_method", custom_resolution_method)
method = MethodRegistry.get("resolution", "custom_method")
if method:
    results = method(conflicts)
```

## Using Registry

### Register Custom Method

```python
from veritasreason.conflicts import MethodRegistry, ResolutionResult

def custom_resolution_method(conflicts, **kwargs):
    """Custom resolution method."""
    # Your custom resolution logic here
    results = []
    for conflict in conflicts:
        # Custom resolution logic
        result = ResolutionResult(
            conflict_id=conflict.conflict_id,
            resolved=True,
            resolved_value="custom_value"
        )
        results.append(result)
    return results

# Register custom method
MethodRegistry.register("resolution", "custom_method", custom_resolution_method)

# Use custom method
method = MethodRegistry.get("resolution", "custom_method")
results = method(conflicts) if method else []
```

### List Registered Methods

```python
from veritasreason.conflicts import MethodRegistry

# List all registered methods
all_methods = MethodRegistry.list_all()
print("Registered methods:")
for task, methods in all_methods.items():
    print(f"  {task}: {methods}")

# List methods for specific task
resolution_methods = MethodRegistry.list_all("resolution")
print(f"Resolution methods: {resolution_methods}")
```

### Unregister Method

```python
from veritasreason.conflicts import MethodRegistry

# Unregister a method
MethodRegistry.unregister("resolution", "custom_method")
```

## Configuration

### Using Configuration Manager

```python
from veritasreason.conflicts import conflicts_config

# Get configuration value
threshold = conflicts_config.get("confidence_threshold", default=0.7)
print(f"Confidence threshold: {threshold}")

# Set configuration value
conflicts_config.set("confidence_threshold", 0.8)

# Get method-specific configuration
method_config = conflicts_config.get_method_config("voting")
print(f"Voting config: {method_config}")

# Set method-specific configuration
conflicts_config.set_method_config("voting", min_sources=2, tie_breaker="confidence")
```

### Environment Variables

```python
# Set environment variables
import os
os.environ["CONFLICT_CONFIDENCE_THRESHOLD"] = "0.8"
os.environ["CONFLICT_DEFAULT_STRATEGY"] = "voting"
os.environ["CONFLICT_TRACK_PROVENANCE"] = "true"

# Configuration will automatically load from environment
from veritasreason.conflicts import conflicts_config
threshold = conflicts_config.get("confidence_threshold")
print(f"Threshold from env: {threshold}")
```

### Config File

```yaml
# config.yaml
conflicts:
  confidence_threshold: 0.8
  default_strategy: "voting"
  track_provenance: true
  auto_resolve: false

conflicts_methods:
  voting:
    min_sources: 2
    tie_breaker: "confidence"
  credibility_weighted:
    min_credibility: 0.5
```

```python
from veritasreason.conflicts import ConflictsConfig

# Load from config file
config = ConflictsConfig(config_file="config.yaml")
threshold = config.get("confidence_threshold")
print(f"Threshold from config: {threshold}")
```

## Advanced Examples

### Complete Workflow

```python
from veritasreason.conflicts import (
    ConflictDetector,
    ConflictResolver,
    ConflictAnalyzer,
    SourceTracker,
    InvestigationGuideGenerator,
    SourceReference
)
from datetime import datetime

# Initialize components
detector = ConflictDetector(confidence_threshold=0.7)
tracker = SourceTracker()
resolver = ConflictResolver()
analyzer = ConflictAnalyzer()
guide_generator = InvestigationGuideGenerator(source_tracker=tracker)

# Track sources
for entity in entities:
    source = SourceReference(
        document=entity.get("source", "unknown"),
        confidence=0.9,
        timestamp=datetime.now()
    )
    tracker.track_property_source(
        entity["id"],
        "name",
        entity.get("name"),
        source
    )

# Detect conflicts
conflicts = detector.detect_value_conflicts(entities, "name")
print(f"Detected {len(conflicts)} conflicts")

# Analyze conflicts
analysis = analyzer.analyze_conflicts(conflicts)
print(f"Analysis: {analysis['total_conflicts']} conflicts found")

# Resolve conflicts - using string strategy
results = resolver.resolve_conflicts(
    conflicts,
    strategy="credibility_weighted"
)

# Generate investigation guides for unresolved conflicts
unresolved = [c for c, r in zip(conflicts, results) if not r.resolved]
guides = guide_generator.generate_guides(unresolved)

for guide in guides:
    print(f"\nInvestigation guide for {guide.conflict_id}:")
    for step in guide.investigation_steps:
        print(f"  {step.step_number}. {step.description}")
```

### Custom Resolution Strategy

```python
from veritasreason.conflicts import (
    ConflictResolver,
    ResolutionResult,
    Conflict
)

class CustomResolver(ConflictResolver):
    def resolve_conflict(self, conflict: Conflict, strategy=None):
        """
        Custom resolution with domain-specific logic.
        
        Note: strategy can be a string (e.g., "voting") or None.
        """
        # Custom logic: prefer values from trusted sources
        trusted_sources = ["doc1", "doc2"]
        
        for i, source in enumerate(conflict.sources):
            if source.get("document") in trusted_sources:
                return ResolutionResult(
                    conflict_id=conflict.conflict_id,
                    resolved=True,
                    resolved_value=conflict.conflicting_values[i],
                    confidence=0.95,
                    sources_used=[source.get("document")],
                    resolution_notes="Resolved using trusted source"
                )
        
        # Fallback to parent method
        return super().resolve_conflict(conflict, strategy)

# Use custom resolver
resolver = CustomResolver()
results = resolver.resolve_conflicts(conflicts)
```

### Batch Conflict Processing

```python
from veritasreason.conflicts import ConflictDetector, ConflictResolver

# Process multiple properties
properties_to_check = ["name", "founded", "revenue", "headquarters"]

detector = ConflictDetector()
resolver = ConflictResolver()

all_results = {}
for property_name in properties_to_check:
    conflicts = detector.detect_value_conflicts(entities, property_name)
    results = resolver.resolve_conflicts(conflicts, strategy="voting")
    all_results[property_name] = {
        "conflicts": conflicts,
        "results": results
    }

# Summary
for prop, data in all_results.items():
    conflicts = data["conflicts"]
    results = data["results"]
    resolved = sum(1 for r in results if r.resolved)
    print(f"{prop}: {len(conflicts)} conflicts, {resolved} resolved")
```

### Conflict Monitoring

```python
from veritasreason.conflicts import ConflictDetector, ConflictAnalyzer

detector = ConflictDetector()
analyzer = ConflictAnalyzer()

# Monitor conflicts over time
conflict_history = []

# Process entities periodically
for batch in entity_batches:
    conflicts = detector.detect_value_conflicts(batch, "name")
    conflict_history.append({
        "timestamp": datetime.now(),
        "conflicts": conflicts,
        "count": len(conflicts)
    })

# Analyze trends
if len(conflict_history) > 1:
    all_conflicts = [c for h in conflict_history for c in h["conflicts"]]
    trends = analyzer.analyze_trends(all_conflicts)
    
    print("Conflict trends:")
    for trend in trends:
        print(f"  {trend['period']}: {trend['conflict_count']} conflicts")
```

