"""
GraphStore — lightweight property graph backed by SQLite.

Stores Entities (nodes) and Relationships (edges) with full CRUD.
"""

import json
import os
import sqlite3
from typing import List, Dict, Any, Optional

from aether.core.state import Entity, EntityType, RelationshipType
from aether.config.settings import settings
from aether.core.logger import logger


class GraphStore:
    """
    A Property Graph using SQLite.
    Suitable for single-process investigations — no external server required.
    """

    def __init__(self, db_path: Optional[str] = None, project_id: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        elif project_id:
            self.db_path = f"aether/data/graphs/{project_id}.db"
        else:
            self.db_path = settings.GRAPH_DB_PATH
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._init_db()

    def clear(self):
        """Wipes all entities and edges from this store."""
        with self._connect() as conn:
            conn.execute("DELETE FROM edges;")
            conn.execute("DELETE FROM nodes;")

    def delete_database_file(self):
        """Removes the SQLite database file from disk completely."""
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                logger.info(f"Deleted graph database file: {self.db_path}")
        except Exception as exc:
            logger.warning(f"Error removing db file {self.db_path}: {exc}")

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id          TEXT PRIMARY KEY,
                    type        TEXT NOT NULL,
                    properties  TEXT DEFAULT '{}',
                    confidence  REAL DEFAULT 1.0,
                    first_seen  TEXT
                );
                CREATE TABLE IF NOT EXISTS edges (
                    source_id   TEXT NOT NULL,
                    target_id   TEXT NOT NULL,
                    rel_type    TEXT NOT NULL,
                    weight      REAL DEFAULT 1.0,
                    metadata    TEXT DEFAULT '{}',
                    PRIMARY KEY (source_id, target_id, rel_type),
                    FOREIGN KEY (source_id) REFERENCES nodes(id),
                    FOREIGN KEY (target_id) REFERENCES nodes(id)
                );
                CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges(target_id);
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Nodes (Entities)
    # ------------------------------------------------------------------

    def add_entity(self, entity: Entity):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nodes (id, type, properties, confidence, first_seen) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    entity.id,
                    entity.type.value,
                    json.dumps(entity.properties),
                    entity.confidence,
                    entity.first_seen.isoformat(),
                ),
            )

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id = ?", (entity_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def query_all_nodes(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM nodes").fetchall()
            return [self._row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Edges (Relationships)
    # ------------------------------------------------------------------

    def add_relationship(
        self,
        rel: RelationshipType,
        source_id: str,
        target_id: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO edges (source_id, target_id, rel_type, weight, metadata) "
                "VALUES (?, ?, ?, ?, ?)",
                (source_id, target_id, rel.value, weight, json.dumps(metadata or {})),
            )

    def get_neighbors(self, entity_id: str) -> List[Dict[str, Any]]:
        """Returns all nodes connected to *entity_id*."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT n.id, n.type, n.properties, e.rel_type, e.weight
                FROM nodes n
                JOIN edges e ON (n.id = e.target_id OR n.id = e.source_id)
                WHERE (e.source_id = ? OR e.target_id = ?) AND n.id != ?
                """,
                (entity_id, entity_id, entity_id),
            ).fetchall()
            return [dict(r) for r in rows]

    def query_all_edges(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM edges").fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        if "properties" in d and isinstance(d["properties"], str):
            d["properties"] = json.loads(d["properties"])
        return d
