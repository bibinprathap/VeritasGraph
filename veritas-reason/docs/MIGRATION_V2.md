## VeritasReason Deduplication V2: Migration & Performance Guide

Welcome to the Deduplication V2 engine!! This release specifically targets severe CI delays and production bottlenecks caused by massive knowledge graph deduplication workloads. By introducing smarter candidate generation, fast-fail prefilters, and semantic triplet canonicalization, we have reduced worst-case execution times by up to **80%**.

**Note:** This upgrade is **100% backward compatible.** All existing scripts, tests, and API signatures will continue to work exactly as they did before.



To utilize this new addition, you must explicitly **opt-in** using the new configuration keys detailed below.

---

### 1. Candidate Generation V2 (Beating the $O(N^2)$ Pair Explosion)

**The Problem:** The legacy engine relied on a naive first-character blocking strategy. If your dataset contained 5,000 companies starting with letter "A", the engine generated nearly 12.5 million candidate pairs.

**The V2 Solution:** Multi-key token blocking, prefix matching, and deterministic candidate budgeting.



**How to Opt-In**

Pass the keys into the `similarity`configuration dictionary when initializing the `DuplicateDetector`:



```python
from veritasreason.deduplication import DuplicateDetector

detector = DuplicateDetector(
    similarity_threshold=0.8,
    similarity = {
    # Switches from legacy to v2
    "candidate_strategy": "blocking_v2",

    # Highly recommended: Limits the max number of comparisons
    # per entity to prevent adversarial latency spikes.
    "max_candidates_per_entity": 50,

    # Optional: Generates blocks using Soundex algorithm to catch
    # phonetic misspellings (e.g, "Jon" vs "John")
    "enable_phonetic_blocking": True
}
)
```



### 2. Two-Stage scoring (The Fast Prefilter)

**The Problem**: Calculating multi-factor semantic scores (Levenshtein, Jaro-Winkler, property intersections, and Embeddings) is computationally expensive. Running these

calculations on two entities that share absolutely zero words or have vastly different string lengths is a waste of resources.

**The V2 Solution:** A lightning-fast prefilter gate that instantly drops obvious non-matches before they ever reach the heavy semantic scorers.



**How to Opt-In**

Enable the prefilter and define your rejection thresholds:



```python
from veritasreason.deduplication import DuplicateDetector

detector = DuplicateDetector(
    similarity_threshold=0.8,
    similarity={
    "candidate_strategy": "blocking_v2",
     
    # Enable prefilter
    "prefilter_enabled": True,

    "prefilter_thresholds": {
    # Rejects pairs if shortest string is less than 40% the length
    # of the longest
    "min_length_ratio": 0.4,
    
    # Instantly rejects pairs if they don't share at least one
    # valid word token
    "required_shared_token": True
},
    # Optional Explainability: Injects a 'score_breakdown' dict into
    # the candidate metadata so you can see exactly how the string,
    # property, and relationships scores contributed.
    
    "score_breakdown_enabled": True
}
)
```



### 3. Semantic Relationship & Triplet Deduplication

**The problem:** The legacy relationship deduplication relied on exact `(Subject, Predicate, Object)` string matches. It couldn't recognize that `(Person, "works_for", Company)` is veritasreasonlly identical to `(Person, "employed_by", Company)` .

**The V2 Solution:** A new `semantic_v2` mode that introduces predicate synonym mapping, literal normalization (cleaning up rogue spaces/casing), and a highly optimized $O(1)$ canonical hash path for fast matching.



**How to Opt-In**

When calling relationship-specific dedup methods, pass the new configuration keys:

```python
from veritasreason.deduplication import DuplicateDetector
from veritasreason.deduplication.methods import dedup_triplets


# Approach A: Using the Detector explicitly
detector = DuplicateDetector()
duplicates = detector.detect_relationship_duplicates(
    relationship_list,
    relationship_dedup_mode="semantic_v2",

    # Cleans up messy object strings 
    # (e.g., "  Apple Inc. " -> "apple inc.")
    literal_normalization_enabled=True,

    # Maps various synonyms to a single canonical predicate
    # before hashing
    predicate_synonym_map={
    "works_for": "employed_by",
    "is_employee_of": "employed_by",
    "has_employer": "employed_by"
}
)


# Approach B: Using the new simplified wrapper in methods.py
duplicates = dedup_triplets(
    relationships_list,
    mode="semantic_v2",
    literal_normalization_enabled=True,
    predicate_synonym_map={"works_for": "employed_by"}
)
```



###### Note on Merge Strategies

When using `semantic_v2` for relationships, the `MergeStrategyManager` will now automatically respect your canonicalized keys. If two entities share a relationship that differs only by a mapped synonym, the engine will correctly identify them as the same relationship and prevent duplicate graph edges during the merge phase.



### Need Help?

If you experience any unexpected behavior when switching from `legacy` to `blocking_v2` or `semantic_v2`, please check the explainability metadata (by setting `"score_breakdown_enabled": True`) to audit the exact scoring process, or open an issue on GitHub.