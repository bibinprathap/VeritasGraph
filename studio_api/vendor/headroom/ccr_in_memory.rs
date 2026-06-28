// Vendored verbatim from headroom: crates/headroom-core/src/ccr/backends/in_memory.rs
// Source: https://github.com/chopratejas/headroom
// This is the reference in-memory CCR backend that studio_api/ccr.py ports to Python.
//
//! In-memory CCR backend.
//!
//! Process-local store backed by [`DashMap`] (sharded concurrent hash
//! map). Distinct keys never contend on the read path; capacity-bound
//! eviction is the only globally-serialized step.

use std::collections::VecDeque;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use dashmap::DashMap;

use crate::ccr::{CcrStore, DEFAULT_CAPACITY, DEFAULT_TTL};

/// In-memory CCR store backed by [`DashMap`] for sharded concurrent
/// access.
///
/// - **TTL**: entries past their TTL are dropped on the next `get`
///   (lazy expiry — no background reaper thread).
/// - **Capacity**: when `put` would push us past capacity, the oldest
///   entry (per insertion order) is evicted.
/// - **Concurrency**: gets and puts on distinct keys do not contend.
pub struct InMemoryCcrStore {
    map: DashMap<String, Entry>,
    /// FIFO insertion order.
    order: Mutex<VecDeque<String>>,
    ttl: Duration,
    capacity: usize,
}

#[derive(Clone)]
struct Entry {
    payload: String,
    inserted: Instant,
}

impl InMemoryCcrStore {
    pub fn new() -> Self {
        Self::with_capacity_and_ttl(DEFAULT_CAPACITY, DEFAULT_TTL)
    }

    pub fn with_capacity_and_ttl(capacity: usize, ttl: Duration) -> Self {
        Self {
            map: DashMap::with_capacity(capacity),
            order: Mutex::new(VecDeque::with_capacity(capacity)),
            ttl,
            capacity,
        }
    }

    /// Sweep the order queue, dropping leading entries that no longer
    /// exist in the map, then evict real entries until under capacity.
    fn evict_until_under_capacity(&self) {
        let mut guard = self.order.lock().expect("ccr order mutex poisoned");
        while self.map.len() >= self.capacity {
            let Some(oldest) = guard.pop_front() else {
                break;
            };
            self.map.remove(&oldest);
        }
    }
}

impl Default for InMemoryCcrStore {
    fn default() -> Self {
        Self::new()
    }
}

impl CcrStore for InMemoryCcrStore {
    fn put(&self, hash: &str, payload: &str) {
        // Idempotent re-store fast-path.
        if let Some(mut existing) = self.map.get_mut(hash) {
            existing.payload = payload.to_string();
            existing.inserted = Instant::now();
            return;
        }

        // New entry. Cap-bound first, then insert and append to FIFO queue.
        if self.map.len() >= self.capacity {
            self.evict_until_under_capacity();
        }
        let entry = Entry {
            payload: payload.to_string(),
            inserted: Instant::now(),
        };
        let prev = self.map.insert(hash.to_string(), entry);
        if prev.is_none() {
            self.order
                .lock()
                .expect("ccr order mutex poisoned")
                .push_back(hash.to_string());
        }
    }

    fn get(&self, hash: &str) -> Option<String> {
        // Read path: shard read-lock, check TTL, clone payload out.
        if let Some(entry) = self.map.get(hash) {
            if entry.inserted.elapsed() <= self.ttl {
                return Some(entry.payload.clone());
            }
        } else {
            return None;
        }
        // Entry exists and looks expired. Re-check under shard write lock
        // via `remove_if` to close the TOCTOU window against a concurrent
        // refreshing `put`.
        let was_removed = self
            .map
            .remove_if(hash, |_, entry| entry.inserted.elapsed() > self.ttl)
            .is_some();
        if was_removed {
            None
        } else {
            self.map.get(hash).map(|e| e.payload.clone())
        }
    }

    fn len(&self) -> usize {
        self.map.len()
    }
}
