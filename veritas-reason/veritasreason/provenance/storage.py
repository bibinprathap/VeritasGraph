"""
Provenance Storage Backends

This module provides storage backends for provenance tracking, including
in-memory and persistent SQLite storage with W3C PROV-O compliance.

Storage Backends:
    - InMemoryStorage: Fast in-memory storage for development/testing
    - SQLiteStorage: Persistent SQLite storage for production use

Features:
    - W3C PROV-O compliant schema
    - Lineage tracing with BFS traversal
    - Efficient entity retrieval
    - Type-based filtering
    - Integrity verification support

Author: VeritasReason Contributors
License: MIT
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import sqlite3
import json
from collections import deque

from .schemas import ProvenanceEntry


class ProvenanceStorage(ABC):
    """
    Abstract storage interface for provenance tracking.
    
    All storage backends must implement these methods to ensure
    consistent provenance tracking across different storage types.
    """
    
    @abstractmethod
    def store(self, entry: ProvenanceEntry) -> None:
        """
        Store a provenance entry.
        
        Args:
            entry: ProvenanceEntry to store
        """
        pass
    
    @abstractmethod
    def retrieve(self, entity_id: str) -> Optional[ProvenanceEntry]:
        """
        Retrieve a provenance entry by entity ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            ProvenanceEntry if found, None otherwise
        """
        pass
    
    @abstractmethod
    def retrieve_all(self, entity_type: Optional[str] = None) -> List[ProvenanceEntry]:
        """
        Retrieve all provenance entries, optionally filtered by type.
        
        Args:
            entity_type: Optional entity type filter
            
        Returns:
            List of ProvenanceEntry objects
        """
        pass
    
    @abstractmethod
    def trace_lineage(self, entity_id: str) -> List[ProvenanceEntry]:
        """
        Trace complete lineage for an entity.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            List of ProvenanceEntry objects in lineage chain
        """
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """
        Clear all provenance data.
        
        Returns:
            Number of entries cleared
        """
        pass


class InMemoryStorage(ProvenanceStorage):
    """
    Fast in-memory storage for provenance tracking.
    
    Suitable for:
        - Development and testing
        - Short-lived processes
        - Small to medium datasets
        - When persistence is not required
    
    Features:
        - O(1) entity retrieval
        - BFS lineage tracing
        - Type-based filtering
        - No external dependencies
    
    Example:
        >>> storage = InMemoryStorage()
        >>> storage.store(entry)
        >>> lineage = storage.trace_lineage("entity_123")
    """
    
    def __init__(self):
        """Initialize in-memory storage."""
        self._entries: Dict[str, ProvenanceEntry] = {}
    
    def store(self, entry: ProvenanceEntry) -> None:
        """
        Store a provenance entry in memory.
        
        Args:
            entry: ProvenanceEntry to store
        """
        self._entries[entry.entity_id] = entry
    
    def retrieve(self, entity_id: str) -> Optional[ProvenanceEntry]:
        """
        Retrieve a provenance entry by entity ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            ProvenanceEntry if found, None otherwise
        """
        return self._entries.get(entity_id)
    
    def retrieve_all(self, entity_type: Optional[str] = None) -> List[ProvenanceEntry]:
        """
        Retrieve all provenance entries, optionally filtered by type.
        
        Args:
            entity_type: Optional entity type filter
            
        Returns:
            List of ProvenanceEntry objects
        """
        if entity_type:
            return [
                entry for entry in self._entries.values()
                if entry.entity_type == entity_type
            ]
        return list(self._entries.values())
    
    def trace_lineage(self, entity_id: str) -> List[ProvenanceEntry]:
        """
        Trace complete lineage using BFS traversal.
        
        Traces both parent entities (wasDerivedFrom) and used entities
        to build complete provenance chain.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            List of ProvenanceEntry objects in lineage chain
        """
        lineage = []
        visited = set()
        queue = deque([entity_id])
        
        while queue:
            current_id = queue.popleft()
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            entry = self.retrieve(current_id)
            
            if entry:
                lineage.append(entry)
                
                # Add parent entity to queue
                if entry.parent_entity_id:
                    queue.append(entry.parent_entity_id)
                
                # Add used entities to queue
                for used_id in entry.used_entities:
                    if used_id not in visited:
                        queue.append(used_id)
        
        return lineage
    
    def clear(self) -> int:
        """
        Clear all provenance data.
        
        Returns:
            Number of entries cleared
        """
        count = len(self._entries)
        self._entries.clear()
        return count


class SQLiteStorage(ProvenanceStorage):
    """
    Persistent SQLite storage for provenance tracking.
    
    Suitable for:
        - Production use
        - Long-term provenance tracking
        - Large datasets
        - Audit trail requirements
        - Regulatory compliance
    
    Features:
        - W3C PROV-O compliant schema
        - Persistent storage
        - Efficient indexing
        - Transaction support
        - Integrity verification
    
    Example:
        >>> storage = SQLiteStorage("provenance.db")
        >>> storage.store(entry)
        >>> lineage = storage.trace_lineage("entity_123")
    """
    
    def __init__(self, db_path: str = "provenance.db"):
        """
        Initialize SQLite storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Create tables with W3C PROV-O compliant schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS provenance (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                agent_id TEXT DEFAULT 'veritasreason',
                source_document TEXT,
                source_location TEXT,
                source_quote TEXT,
                timestamp TEXT NOT NULL,
                first_seen TEXT,
                last_updated TEXT,
                confidence REAL DEFAULT 1.0,
                checksum TEXT,
                parent_entity_id TEXT,
                used_entities TEXT,
                start_index INTEGER,
                end_index INTEGER,
                credibility REAL,
                metadata TEXT,
                version TEXT DEFAULT '1.0'
            )
        """)
        
        # Create indexes for efficient querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_type 
            ON provenance(entity_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_document 
            ON provenance(source_document)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_parent_entity 
            ON provenance(parent_entity_id)
        """)
        
        conn.commit()
        conn.close()
    
    def store(self, entry: ProvenanceEntry) -> None:
        """
        Store a provenance entry in SQLite database.
        
        Args:
            entry: ProvenanceEntry to store
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO provenance VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                entry.entity_id,
                entry.entity_type,
                entry.activity_id,
                entry.agent_id,
                entry.source_document,
                entry.source_location,
                entry.source_quote,
                entry.timestamp,
                entry.first_seen,
                entry.last_updated,
                entry.confidence,
                entry.checksum,
                entry.parent_entity_id,
                json.dumps(entry.used_entities),
                entry.start_index,
                entry.end_index,
                entry.credibility,
                json.dumps(entry.metadata),
                entry.version
            ))
            
            conn.commit()
        finally:
            conn.close()
    
    def retrieve(self, entity_id: str) -> Optional[ProvenanceEntry]:
        """
        Retrieve a provenance entry by entity ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            ProvenanceEntry if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM provenance WHERE entity_id = ?
            """, (entity_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return self._row_to_entry(row)
        finally:
            conn.close()
    
    def retrieve_all(self, entity_type: Optional[str] = None) -> List[ProvenanceEntry]:
        """
        Retrieve all provenance entries, optionally filtered by type.
        
        Args:
            entity_type: Optional entity type filter
            
        Returns:
            List of ProvenanceEntry objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if entity_type:
                cursor.execute("""
                    SELECT * FROM provenance WHERE entity_type = ?
                """, (entity_type,))
            else:
                cursor.execute("SELECT * FROM provenance")
            
            rows = cursor.fetchall()
            return [self._row_to_entry(row) for row in rows]
        finally:
            conn.close()
    
    def trace_lineage(self, entity_id: str) -> List[ProvenanceEntry]:
        """
        Trace complete lineage using BFS traversal.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            List of ProvenanceEntry objects in lineage chain
        """
        lineage = []
        visited = set()
        queue = deque([entity_id])
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            while queue:
                current_id = queue.popleft()
                
                if current_id in visited:
                    continue
                
                visited.add(current_id)
                
                cursor.execute("""
                    SELECT * FROM provenance WHERE entity_id = ?
                """, (current_id,))
                
                row = cursor.fetchone()
                if row:
                    entry = self._row_to_entry(row)
                    lineage.append(entry)
                    
                    # Add parent entity to queue
                    if entry.parent_entity_id:
                        queue.append(entry.parent_entity_id)
                    
                    # Add used entities to queue
                    for used_id in entry.used_entities:
                        if used_id not in visited:
                            queue.append(used_id)
            
            return lineage
        finally:
            conn.close()
    
    def clear(self) -> int:
        """
        Clear all provenance data.
        
        Returns:
            Number of entries cleared
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM provenance")
            count = cursor.fetchone()[0]
            
            cursor.execute("DELETE FROM provenance")
            conn.commit()
            
            return count
        finally:
            conn.close()
    
    def _row_to_entry(self, row: tuple) -> ProvenanceEntry:
        """
        Convert database row to ProvenanceEntry.
        
        Args:
            row: Database row tuple
            
        Returns:
            ProvenanceEntry object
        """
        return ProvenanceEntry(
            entity_id=row[0],
            entity_type=row[1],
            activity_id=row[2],
            agent_id=row[3],
            source_document=row[4] or "",
            source_location=row[5],
            source_quote=row[6],
            timestamp=row[7],
            first_seen=row[8],
            last_updated=row[9],
            confidence=row[10],
            checksum=row[11],
            parent_entity_id=row[12],
            used_entities=json.loads(row[13]) if row[13] else [],
            start_index=row[14],
            end_index=row[15],
            credibility=row[16],
            metadata=json.loads(row[17]) if row[17] else {},
            version=row[18]
        )
