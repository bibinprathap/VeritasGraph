// Vendored verbatim from headroom: crates/headroom-core/src/ccr/mod.rs
// Source: https://github.com/chopratejas/headroom
// Kept in-tree as the reference implementation that studio_api/ccr.py ports.
//
//! CCR (Compress-Cache-Retrieve) storage layer.
//!
//! When a transform compresses data with row-drop or opaque-string
//! substitution, the *original payload* is stashed here keyed by the
//! hash that ends up in the prompt. The runtime later honors retrieval
//! tool calls by looking up the hash in this store and serving back the
//! original. This is the cornerstone of CCR: lossy on the wire, lossless
//! end-to-end.

pub mod backends;

use std::time::Duration;

pub use backends::{from_config, CcrBackendConfig, CcrBackendInitError, InMemoryCcrStore};

/// Pluggable CCR storage backend. `Send + Sync` so it can sit behind an
/// `Arc` and be shared across threads in the proxy.
pub trait CcrStore: Send + Sync {
    /// Stash `payload` under `hash`. If the hash already exists, the
    /// new payload overwrites — same hash should mean same content, so
    /// re-storing is idempotent.
    fn put(&self, hash: &str, payload: &str);

    /// Look up `hash`. Returns `None` if missing or expired.
    fn get(&self, hash: &str) -> Option<String>;

    /// Number of live entries. Informational; used by tests + telemetry.
    fn len(&self) -> usize;

    fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// Default capacity — matches Python's `CompressionStore` default.
pub const DEFAULT_CAPACITY: usize = 1000;

/// Default TTL — 30 minutes, matching Python (`CCRConfig.store_ttl_seconds`).
pub const DEFAULT_TTL: Duration = Duration::from_secs(1800);

/// Compute the canonical CCR key for `payload`. BLAKE3 → first 24 hex
/// chars (96 bits — collision-resistant for the bounded LRU population
/// the proxy will hold).
pub fn compute_key(payload: &[u8]) -> String {
    let h = blake3::hash(payload);
    let hex = h.to_hex();
    // Stable 24-char prefix matches the Python tool-injection regex
    // (`[a-f0-9]{24}`).
    hex.as_str()[..24].to_string()
}

/// Standard `<<ccr:HASH>>` marker injected into compressed block content
/// so the runtime can later look up the original bytes when the model
/// calls `headroom_retrieve`.
pub fn marker_for(hash: &str) -> String {
    format!("<<ccr:{hash}>>")
}
