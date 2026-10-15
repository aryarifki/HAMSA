"""
HAMSA Enterprise Database Engine
Production-grade PostgreSQL database manager with asyncpg connection pooling,
automatic schema migration (Auto-DDL), and high-performance JSONB indexing.
Supports graceful fallback to SQLite when operating in standalone mode.
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

# Load .env if python-dotenv is present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from hamsa.core.models import EntityNode, RelationEdge, TargetType, RelationType
from hamsa.core.graph import KnowledgeGraph
from hamsa.utils.formatters import log_info, log_success, log_error, log_warn


class DatabaseManager:
    """Enterprise Database Manager supporting PostgreSQL (primary) and SQLite (fallback)."""

    def __init__(self, dsn: Optional[str] = None):
        self.engine_type = os.getenv("HAMSA_DB_ENGINE", "postgres").lower()
        self.dsn = dsn or os.getenv("DATABASE_URL")
        
        if not self.dsn and self.engine_type == "postgres":
            user = os.getenv("POSTGRES_USER", "hamsa_admin")
            pwd = os.getenv("POSTGRES_PASSWORD", "hamsa_secure_password_2026")
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            db = os.getenv("POSTGRES_DB", "hamsa_intelligence")
            self.dsn = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

        self.sqlite_path = os.path.expanduser(os.getenv("SQLITE_DB_PATH", "~/.hamsa/hamsa.db"))
        self.pg_pool = None
        self._connected = False

    async def connect(self) -> bool:
        """Initializes database connection pool and executes Auto-DDL migrations."""
        if self._connected:
            return True

        if self.engine_type == "postgres":
            try:
                import asyncpg
                log_info(f"Connecting to enterprise PostgreSQL at: {self.dsn.split('@')[-1] if '@' in self.dsn else 'localhost'}")
                self.pg_pool = await asyncpg.create_pool(
                    dsn=self.dsn,
                    min_size=int(os.getenv("PG_POOL_MIN", "2")),
                    max_size=int(os.getenv("PG_POOL_MAX", "10")),
                    command_timeout=60,
                    timeout=5.0
                )
                await self._migrate_postgres()
                await self.bootstrap_default_admin()
                self._connected = True
                log_success("PostgreSQL connection pool established with Auto-DDL schema verification.")
                return True
            except Exception as e:
                log_warn(f"PostgreSQL connection failed ({e}). Reverting to local SQLite fallback.")
                self.engine_type = "sqlite"

        # SQLite Fallback Engine
        await self._migrate_sqlite()
        await self.bootstrap_default_admin()
        self._connected = True
        log_info(f"Using local SQLite database at: {self.sqlite_path}")
        return True

    async def close(self) -> None:
        """Closes PostgreSQL pool gracefully on shutdown."""
        if self.pg_pool:
            await self.pg_pool.close()
            self.pg_pool = None
        self._connected = False

    async def _migrate_postgres(self) -> None:
        """Executes idempotent PostgreSQL DDL migrations and GIN indexing."""
        async with self.pg_pool.acquire() as conn:
            # Enable pgcrypto for UUID generation if supported
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";")
            except Exception:
                pass

            await conn.execute("""
                -- 1. Users Table (Investigator RBAC)
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(64) PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20) DEFAULT 'investigator',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- 2. Audit Logs Table
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id BIGSERIAL PRIMARY KEY,
                    user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
                    action VARCHAR(100) NOT NULL,
                    target VARCHAR(255),
                    metadata JSONB DEFAULT '{}'::jsonb,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- 3. Cases Table (Dossier Projects)
                CREATE TABLE IF NOT EXISTS cases (
                    id VARCHAR(100) PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT DEFAULT '',
                    status VARCHAR(50) DEFAULT 'active',
                    tags JSONB DEFAULT '["Active"]'::jsonb,
                    notes TEXT DEFAULT '',
                    evidence JSONB DEFAULT '[]'::jsonb,
                    targets JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- 4. Scans Table
                CREATE TABLE IF NOT EXISTS scans (
                    id VARCHAR(100) PRIMARY KEY,
                    case_id VARCHAR(100) REFERENCES cases(id) ON DELETE CASCADE,
                    targets_input JSONB NOT NULL,
                    depth INT DEFAULT 1,
                    status VARCHAR(50) DEFAULT 'completed',
                    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP WITH TIME ZONE
                );

                -- 5. Knowledge Graph Nodes
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id VARCHAR(255) NOT NULL,
                    case_id VARCHAR(100) REFERENCES cases(id) ON DELETE CASCADE,
                    node_type VARCHAR(50) NOT NULL,
                    value VARCHAR(500) NOT NULL,
                    label VARCHAR(500),
                    attributes JSONB DEFAULT '{}'::jsonb,
                    source_plugin VARCHAR(100),
                    confidence FLOAT DEFAULT 1.0,
                    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id, case_id)
                );

                -- 6. Knowledge Graph Edges
                CREATE TABLE IF NOT EXISTS graph_edges (
                    id BIGSERIAL PRIMARY KEY,
                    case_id VARCHAR(100) REFERENCES cases(id) ON DELETE CASCADE,
                    source_id VARCHAR(255) NOT NULL,
                    target_id VARCHAR(255) NOT NULL,
                    relation_type VARCHAR(100) NOT NULL,
                    label VARCHAR(255),
                    weight FLOAT DEFAULT 1.0,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    UNIQUE(source_id, target_id, relation_type, case_id)
                );

                -- 7. Continuous Surveillance Watchlist
                CREATE TABLE IF NOT EXISTS watchlist (
                    id VARCHAR(100) PRIMARY KEY,
                    target_value VARCHAR(255) NOT NULL,
                    target_type VARCHAR(50) NOT NULL,
                    last_checked TIMESTAMP WITH TIME ZONE,
                    last_diff_score INT DEFAULT 0,
                    webhook_url TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    UNIQUE(target_value, target_type)
                );

                -- Indexes for fast lookup & JSONB querying
                CREATE INDEX IF NOT EXISTS idx_graph_nodes_attributes ON graph_nodes USING GIN (attributes);
                CREATE INDEX IF NOT EXISTS idx_graph_nodes_case_type ON graph_nodes (case_id, node_type);
                CREATE INDEX IF NOT EXISTS idx_graph_edges_case ON graph_edges (case_id);
                CREATE INDEX IF NOT EXISTS idx_cases_updated ON cases (updated_at DESC);
            """)

    async def _migrate_sqlite(self) -> None:
        """Executes idempotent SQLite migrations for standalone offline mode."""
        import sqlite3
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)

        def _sync_schema():
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT DEFAULT 'investigator',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        action TEXT NOT NULL,
                        target TEXT,
                        metadata TEXT DEFAULT '{}',
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS scans (
                        id TEXT PRIMARY KEY,
                        case_id TEXT NOT NULL,
                        targets_input TEXT NOT NULL,
                        depth INTEGER DEFAULT 1,
                        status TEXT DEFAULT 'completed',
                        progress_percent INTEGER DEFAULT 100,
                        started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        finished_at DATETIME
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cases (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        status TEXT DEFAULT 'active',
                        tags TEXT DEFAULT '["Active"]',
                        notes TEXT DEFAULT '',
                        evidence TEXT DEFAULT '[]',
                        targets TEXT DEFAULT '[]',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS graph_nodes (
                        id TEXT NOT NULL,
                        case_id TEXT NOT NULL,
                        node_type TEXT NOT NULL,
                        value TEXT NOT NULL,
                        label TEXT,
                        attributes TEXT DEFAULT '{}',
                        source_plugin TEXT,
                        confidence REAL DEFAULT 1.0,
                        discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (id, case_id)
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS graph_edges (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        case_id TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        relation_type TEXT NOT NULL,
                        label TEXT,
                        weight REAL DEFAULT 1.0,
                        metadata TEXT DEFAULT '{}',
                        UNIQUE(source_id, target_id, relation_type, case_id)
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS watchlist (
                        id TEXT PRIMARY KEY,
                        target_value TEXT NOT NULL,
                        target_type TEXT NOT NULL,
                        last_checked DATETIME,
                        last_diff_score INTEGER DEFAULT 0,
                        webhook_url TEXT,
                        is_active INTEGER DEFAULT 1,
                        UNIQUE(target_value, target_type)
                    );
                """)
        await asyncio.to_thread(_sync_schema)

    # --------------------------------------------------------------------------
    # CASE & DOSSIER OPERATIONS
    # --------------------------------------------------------------------------

    async def get_or_create_case(self, case_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Fetches an existing case or creates a new one if not found."""
        existing = await self.get_case(case_id)
        if existing:
            return existing
        return await self.create_case(
            case_id=case_id,
            title=title or f"Investigation Dossier ({case_id})",
            description="Auto-generated investigation case workspace"
        )

    async def create_case(
        self,
        title: str,
        case_id: Optional[str] = None,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Creates a new investigation case."""
        cid = case_id or f"case_{int(datetime.now().timestamp())}"
        tag_list = tags or ["Active"]
        now_iso = datetime.now().isoformat()

        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO cases (id, title, description, tags, updated_at)
                    VALUES ($1, $2, $3, $4::jsonb, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE
                    SET title = EXCLUDED.title, description = EXCLUDED.description, updated_at = CURRENT_TIMESTAMP
                """, cid, title, description, json.dumps(tag_list))
        else:
            def _sync_create():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO cases (id, title, description, tags, updated_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (cid, title, description, json.dumps(tag_list)))
            await asyncio.to_thread(_sync_create)

        return {
            "id": cid,
            "title": title,
            "description": description,
            "tags": tag_list,
            "status": "active",
            "notes": "",
            "evidence": [],
            "targets": [],
            "updated_at": now_iso
        }

    async def list_cases(self) -> List[Dict[str, Any]]:
        """Lists all active and archived cases with entity counts."""
        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT c.id, c.title, c.description, c.status, c.tags, c.notes, c.evidence, c.targets, c.updated_at,
                           COUNT(DISTINCT n.id) AS entity_count,
                           COUNT(DISTINCT e.id) AS relation_count
                    FROM cases c
                    LEFT JOIN graph_nodes n ON c.id = n.case_id
                    LEFT JOIN graph_edges e ON c.id = e.case_id
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC
                """)
                return [
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "description": r["description"],
                        "status": r["status"],
                        "tags": json.loads(r["tags"]) if isinstance(r["tags"], str) else (r["tags"] or []),
                        "notes": r["notes"] or "",
                        "evidence": json.loads(r["evidence"]) if isinstance(r["evidence"], str) else (r["evidence"] or []),
                        "targets": json.loads(r["targets"]) if isinstance(r["targets"], str) else (r["targets"] or []),
                        "updated_at": r["updated_at"].isoformat() if hasattr(r["updated_at"], "isoformat") else str(r["updated_at"]),
                        "entity_count": r["entity_count"],
                        "relation_count": r["relation_count"]
                    }
                    for r in rows
                ]
        else:
            def _sync_list():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute("""
                        SELECT c.id, c.title, c.description, c.status, c.tags, c.notes, c.evidence, c.targets, c.updated_at,
                               COUNT(DISTINCT n.id) AS entity_count,
                               COUNT(DISTINCT e.id) AS relation_count
                        FROM cases c
                        LEFT JOIN graph_nodes n ON c.id = n.case_id
                        LEFT JOIN graph_edges e ON c.id = e.case_id
                        GROUP BY c.id
                        ORDER BY c.updated_at DESC
                    """).fetchall()
                    return [
                        {
                            "id": r["id"],
                            "title": r["title"],
                            "description": r["description"],
                            "status": r["status"],
                            "tags": json.loads(r["tags"] or "[]"),
                            "notes": r["notes"] or "",
                            "evidence": json.loads(r["evidence"] or "[]"),
                            "targets": json.loads(r["targets"] or "[]"),
                            "updated_at": str(r["updated_at"]),
                            "entity_count": r["entity_count"],
                            "relation_count": r["relation_count"]
                        }
                        for r in rows
                    ]
            return await asyncio.to_thread(_sync_list)

    async def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full case details including graph data and evidence."""
        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                r = await conn.fetchrow("SELECT * FROM cases WHERE id = $1", case_id)
                if not r:
                    return None
                graph = await self.load_graph(case_id)
                return {
                    "id": r["id"],
                    "title": r["title"],
                    "description": r["description"],
                    "status": r["status"],
                    "tags": json.loads(r["tags"]) if isinstance(r["tags"], str) else (r["tags"] or []),
                    "notes": r["notes"] or "",
                    "evidence": json.loads(r["evidence"]) if isinstance(r["evidence"], str) else (r["evidence"] or []),
                    "targets": json.loads(r["targets"]) if isinstance(r["targets"], str) else (r["targets"] or []),
                    "updated_at": r["updated_at"].isoformat() if hasattr(r["updated_at"], "isoformat") else str(r["updated_at"]),
                    "graph_data": graph.to_dict()
                }
        else:
            def _sync_get():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    r = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
                    if not r:
                        return None
                    return {
                        "id": r["id"],
                        "title": r["title"],
                        "description": r["description"],
                        "status": r["status"],
                        "tags": json.loads(r["tags"] or "[]"),
                        "notes": r["notes"] or "",
                        "evidence": json.loads(r["evidence"] or "[]"),
                        "targets": json.loads(r["targets"] or "[]"),
                        "updated_at": str(r["updated_at"])
                    }
            case_data = await asyncio.to_thread(_sync_get)
            if case_data:
                graph = await self.load_graph(case_id)
                case_data["graph_data"] = graph.to_dict()
            return case_data

    # --------------------------------------------------------------------------
    # KNOWLEDGE GRAPH PERSISTENCE
    # --------------------------------------------------------------------------

    async def save_graph(self, case_id: str, graph: KnowledgeGraph, targets: Optional[List[Tuple[str, TargetType]]] = None) -> None:
        """Persists KnowledgeGraph nodes and edges to the database associated with case_id."""
        await self.get_or_create_case(case_id)

        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                async with conn.transaction():
                    # 1. Update Case targets & timestamp
                    if targets:
                        target_objs = [{"value": t[0], "type": t[1].value} for t in targets]
                        await conn.execute("""
                            UPDATE cases
                            SET targets = cases.targets || $2::jsonb, updated_at = CURRENT_TIMESTAMP
                            WHERE id = $1
                        """, case_id, json.dumps(target_objs))
                    else:
                        await conn.execute("UPDATE cases SET updated_at = CURRENT_TIMESTAMP WHERE id = $1", case_id)

                    # 2. Bulk upsert nodes
                    if graph.nodes:
                        node_tuples = [
                            (
                                n.id,
                                case_id,
                                n.type.value,
                                n.value,
                                n.label,
                                json.dumps(n.attributes, ensure_ascii=False),
                                n.source_plugin,
                                n.confidence
                            )
                            for n in graph.nodes.values()
                        ]
                        await conn.executemany("""
                            INSERT INTO graph_nodes (id, case_id, node_type, value, label, attributes, source_plugin, confidence)
                            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
                            ON CONFLICT (id, case_id) DO UPDATE
                            SET attributes = graph_nodes.attributes || EXCLUDED.attributes,
                                label = COALESCE(EXCLUDED.label, graph_nodes.label),
                                confidence = GREATEST(graph_nodes.confidence, EXCLUDED.confidence)
                        """, node_tuples)

                    # 3. Bulk insert edges
                    if graph.edges:
                        edge_tuples = [
                            (
                                case_id,
                                e.source_id,
                                e.target_id,
                                e.relation_type.value,
                                e.label,
                                e.weight,
                                json.dumps(e.metadata, ensure_ascii=False)
                            )
                            for e in graph.edges
                        ]
                        await conn.executemany("""
                            INSERT INTO graph_edges (case_id, source_id, target_id, relation_type, label, weight, metadata)
                            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                            ON CONFLICT (source_id, target_id, relation_type, case_id) DO NOTHING
                        """, edge_tuples)
        else:
            def _sync_save():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    # Update targets
                    if targets:
                        target_objs = [{"value": t[0], "type": t[1].value} for t in targets]
                        conn.execute("UPDATE cases SET targets = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(target_objs), case_id))

                    # Insert nodes
                    for n in graph.nodes.values():
                        conn.execute("""
                            INSERT INTO graph_nodes (id, case_id, node_type, value, label, attributes, source_plugin, confidence)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id, case_id) DO UPDATE SET
                                attributes = excluded.attributes,
                                label = coalesce(excluded.label, graph_nodes.label),
                                confidence = max(graph_nodes.confidence, excluded.confidence)
                        """, (n.id, case_id, n.type.value, n.value, n.label, json.dumps(n.attributes), n.source_plugin, n.confidence))

                    # Insert edges
                    for e in graph.edges:
                        conn.execute("""
                            INSERT OR IGNORE INTO graph_edges (case_id, source_id, target_id, relation_type, label, weight, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (case_id, e.source_id, e.target_id, e.relation_type.value, e.label, e.weight, json.dumps(e.metadata)))
            await asyncio.to_thread(_sync_save)

    async def load_graph(self, case_id: str) -> KnowledgeGraph:
        """Hydrates a KnowledgeGraph instance from database for case_id."""
        graph = KnowledgeGraph()

        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                nodes = await conn.fetch("SELECT * FROM graph_nodes WHERE case_id = $1", case_id)
                for r in nodes:
                    attrs = json.loads(r["attributes"]) if isinstance(r["attributes"], str) else (r["attributes"] or {})
                    node = EntityNode(
                        id=r["id"],
                        type=TargetType(r["node_type"]),
                        value=r["value"],
                        label=r["label"],
                        attributes=attrs,
                        source_plugin=r["source_plugin"],
                        confidence=r["confidence"]
                    )
                    graph.add_node(node)

                edges = await conn.fetch("SELECT * FROM graph_edges WHERE case_id = $1", case_id)
                for r in edges:
                    meta = json.loads(r["metadata"]) if isinstance(r["metadata"], str) else (r["metadata"] or {})
                    edge = RelationEdge(
                        source_id=r["source_id"],
                        target_id=r["target_id"],
                        relation_type=RelationType(r["relation_type"]),
                        label=r["label"] or "",
                        weight=r["weight"],
                        metadata=meta
                    )
                    graph.add_edge(edge)
        else:
            def _sync_load():
                import sqlite3
                nodes_res, edges_res = [], []
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    nodes_res = conn.execute("SELECT * FROM graph_nodes WHERE case_id = ?", (case_id,)).fetchall()
                    edges_res = conn.execute("SELECT * FROM graph_edges WHERE case_id = ?", (case_id,)).fetchall()
                return nodes_res, edges_res

            nodes_res, edges_res = await asyncio.to_thread(_sync_load)
            for r in nodes_res:
                node = EntityNode(
                    id=r["id"],
                    type=TargetType(r["node_type"]),
                    value=r["value"],
                    label=r["label"],
                    attributes=json.loads(r["attributes"] or "{}"),
                    source_plugin=r["source_plugin"],
                    confidence=r["confidence"]
                )
                graph.add_node(node)

            for r in edges_res:
                edge = RelationEdge(
                    source_id=r["source_id"],
                    target_id=r["target_id"],
                    relation_type=RelationType(r["relation_type"]),
                    label=r["label"] or "",
                    weight=r["weight"],
                    metadata=json.loads(r["metadata"] or "{}")
                )
                graph.add_edge(edge)

        return graph

    # --------------------------------------------------------------------------
    # FORENSIC ANNOTATION & EVIDENCE
    # --------------------------------------------------------------------------

    async def annotate_node(
        self,
        case_id: str,
        node_id: str,
        tag: Optional[str] = None,
        color: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Applies investigator markings (e.g. 'Primary Suspect', 'Verified Lead') to a node."""
        patch = {}
        if tag is not None:
            patch["investigator_tag"] = tag
        if color is not None:
            patch["custom_color"] = color
        if notes is not None:
            patch["investigator_notes"] = notes

        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                res = await conn.execute("""
                    UPDATE graph_nodes
                    SET attributes = graph_nodes.attributes || $3::jsonb
                    WHERE id = $1 AND case_id = $2
                """, node_id, case_id, json.dumps(patch))
                return "UPDATE 1" in res
        else:
            def _sync_annotate():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cur = conn.execute("SELECT attributes FROM graph_nodes WHERE id = ? AND case_id = ?", (node_id, case_id)).fetchone()
                    if not cur:
                        return False
                    existing = json.loads(cur["attributes"] or "{}")
                    existing.update(patch)
                    conn.execute("UPDATE graph_nodes SET attributes = ? WHERE id = ? AND case_id = ?", (json.dumps(existing), node_id, case_id))
                    return True
            return await asyncio.to_thread(_sync_annotate)

    async def update_case_notes(self, case_id: str, notes: str) -> bool:
        """Saves forensic investigator notes to the case dossier."""
        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                res = await conn.execute("UPDATE cases SET notes = $2, updated_at = CURRENT_TIMESTAMP WHERE id = $1", case_id, notes)
                return "UPDATE 1" in res
        else:
            def _sync_notes():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.execute("UPDATE cases SET notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (notes, case_id))
                    return True
            return await asyncio.to_thread(_sync_notes)

    async def add_evidence(
        self,
        case_id: str,
        url: str,
        title: str,
        evidence_type: str = "web_snapshot",
        notes: str = ""
    ) -> Dict[str, Any]:
        """Appends digital forensic evidence to the case record."""
        ev_id = f"ev_{int(datetime.now().timestamp())}"
        ev_item = {
            "id": ev_id,
            "url": url,
            "title": title,
            "evidence_type": evidence_type,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        }

        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE cases
                    SET evidence = cases.evidence || $2::jsonb, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, case_id, json.dumps([ev_item]))
        else:
            def _sync_evidence():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    r = conn.execute("SELECT evidence FROM cases WHERE id = ?", (case_id,)).fetchone()
                    ev_list = json.loads(r["evidence"] or "[]") if r else []
                    ev_list.append(ev_item)
                    conn.execute("UPDATE cases SET evidence = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(ev_list), case_id))
            await asyncio.to_thread(_sync_evidence)

        return ev_item

    # --------------------------------------------------------------------------
    # CHRONOFORENSIC TIMELINE EXTRACTION
    # --------------------------------------------------------------------------

    async def get_timeline_events(self, case_id: str) -> List[Dict[str, Any]]:
        """Extracts chronological events (EXIF dates, breach years, malware logs) for a case."""
        graph = await self.load_graph(case_id)
        events = []

        for node in graph.nodes.values():
            attrs = node.attributes
            # 1. EXIF Timestamp
            exif_time = attrs.get("exif_datetime") or attrs.get("timestamp")
            if exif_time:
                events.append({
                    "timestamp": str(exif_time),
                    "title": f"Camera Capture: {node.label or node.value}",
                    "category": "exif",
                    "node_id": node.id,
                    "description": f"Camera: {attrs.get('camera_make', '')} {attrs.get('camera_model', '')}. GPS: {attrs.get('gps_location', 'None')}",
                    "severity": "low"
                })

            # 2. Breach Date
            breach_date = attrs.get("breach_date") or attrs.get("breach_year")
            if breach_date:
                events.append({
                    "timestamp": str(breach_date),
                    "title": f"Breach Incident: {attrs.get('breach_title') or node.label}",
                    "category": "breach",
                    "node_id": node.id,
                    "description": f"Compromised Data: {', '.join(attrs.get('compromised_data', [])) if isinstance(attrs.get('compromised_data'), list) else 'Credentials'}",
                    "severity": "critical" if attrs.get("is_sensitive") else "high"
                })

            # 3. Malware Infection Log Date
            stealer_date = attrs.get("date_compromised") or attrs.get("log_timestamp")
            if stealer_date:
                events.append({
                    "timestamp": str(stealer_date),
                    "title": f"Stealer Malware Log: {node.label}",
                    "category": "malware",
                    "node_id": node.id,
                    "description": f"Malware Family: {attrs.get('stealer_family', 'Unknown')}. Operating System: {attrs.get('os', 'Unknown')}",
                    "severity": "critical"
                })

        # Sort chronologically descending
        events.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        return events

    # --------------------------------------------------------------------------
    # RBAC & USER AUTHENTICATION
    # --------------------------------------------------------------------------

    async def bootstrap_default_admin(self) -> None:
        """Bootstraps default administrator account if the users table is empty."""
        from hamsa.core.auth import PasswordHasher
        admin_user = os.getenv("HAMSA_ADMIN_USER", "admin")
        admin_pwd = os.getenv("HAMSA_ADMIN_PASSWORD", "admin_secure_password_2026")

        existing = await self.get_user(admin_user)
        if not existing:
            hashed = PasswordHasher.hash_password(admin_pwd)
            await self.create_user(username=admin_user, password_hash=hashed, role="admin", user_id="usr_admin_default")
            log_info(f"Default admin account initialized (Username: '{admin_user}')")

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieves user record by username."""
        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                r = await conn.fetchrow("SELECT * FROM users WHERE username = $1", username)
                if not r:
                    return None
                return dict(r)
        else:
            def _sync_get_user():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    r = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
                    return dict(r) if r else None
            return await asyncio.to_thread(_sync_get_user)

    async def create_user(
        self,
        username: str,
        password_hash: str,
        role: str = "investigator",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new user account with investigator or admin role."""
        uid = user_id or f"usr_{int(datetime.now().timestamp())}"
        now_iso = datetime.now().isoformat()

        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (id, username, password_hash, role)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (username) DO UPDATE
                    SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role
                """, uid, username, password_hash, role)
        else:
            def _sync_create_user():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO users (id, username, password_hash, role)
                        VALUES (?, ?, ?, ?)
                    """, (uid, username, password_hash, role))
            await asyncio.to_thread(_sync_create_user)

        return {
            "id": uid,
            "username": username,
            "role": role,
            "created_at": now_iso
        }

    async def list_users(self) -> List[Dict[str, Any]]:
        """Lists all registered users (excluding password hashes)."""
        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch("SELECT id, username, role, created_at FROM users ORDER BY created_at ASC")
                return [dict(r) for r in rows]
        else:
            def _sync_list_users():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at ASC").fetchall()
                    return [dict(r) for r in rows]
            return await asyncio.to_thread(_sync_list_users)

    # --------------------------------------------------------------------------
    # FORENSIC AUDIT TRAIL LOGGING
    # --------------------------------------------------------------------------

    async def log_audit(
        self,
        user_id: Optional[str],
        action: str,
        target: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Records an auditable investigator action into the forensic ledger."""
        meta = metadata or {}
        if self.engine_type == "postgres" and self.pg_pool:
            try:
                async with self.pg_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO audit_logs (user_id, action, target, metadata)
                        VALUES ($1, $2, $3, $4::jsonb)
                    """, user_id, action, target, json.dumps(meta))
            except Exception as e:
                log_warn(f"Failed to write PostgreSQL audit log: {e}")
        else:
            def _sync_log():
                try:
                    import sqlite3
                    with sqlite3.connect(self.sqlite_path) as conn:
                        conn.execute("""
                            INSERT INTO audit_logs (user_id, action, target, metadata)
                            VALUES (?, ?, ?, ?)
                        """, (user_id, action, target, json.dumps(meta)))
                except Exception:
                    pass
            await asyncio.to_thread(_sync_log)

    async def list_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches the most recent audit trail records."""
        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, user_id, action, target, metadata, timestamp
                    FROM audit_logs
                    ORDER BY timestamp DESC
                    LIMIT $1
                """, limit)
                return [
                    {
                        "id": r["id"],
                        "user_id": r["user_id"],
                        "action": r["action"],
                        "target": r["target"],
                        "metadata": json.loads(r["metadata"]) if isinstance(r["metadata"], str) else (r["metadata"] or {}),
                        "timestamp": r["timestamp"].isoformat() if hasattr(r["timestamp"], "isoformat") else str(r["timestamp"])
                    }
                    for r in rows
                ]
        else:
            def _sync_audit():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute("""
                        SELECT id, user_id, action, target, metadata, timestamp
                        FROM audit_logs
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (limit,)).fetchall()
                    return [
                        {
                            "id": r["id"],
                            "user_id": r["user_id"],
                            "action": r["action"],
                            "target": r["target"],
                            "metadata": json.loads(r["metadata"] or "{}"),
                            "timestamp": str(r["timestamp"])
                        }
                        for r in rows
                    ]
            return await asyncio.to_thread(_sync_audit)

    # --------------------------------------------------------------------------
    # SCAN JOB QUEUE & STATUS TRACKING
    # --------------------------------------------------------------------------

    async def create_scan_record(
        self,
        case_id: str,
        targets: List[Any],
        depth: int = 1,
        initiated_by: Optional[str] = None
    ) -> str:
        """Initializes a new scan state record in the database."""
        scan_id = f"scan_{int(datetime.now().timestamp())}_{secrets.token_hex(3)}"
        target_json = json.dumps([{"value": t[0] if isinstance(t, (list, tuple)) else str(t)} for t in targets])

        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO scans (id, case_id, targets_input, depth, status, started_at)
                    VALUES ($1, $2, $3::jsonb, $4, 'running', CURRENT_TIMESTAMP)
                """, scan_id, case_id, target_json, depth)
        else:
            def _sync_create_scan():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.execute("""
                        INSERT INTO scans (id, case_id, targets_input, depth, status, progress_percent, started_at)
                        VALUES (?, ?, ?, ?, 'running', 10, CURRENT_TIMESTAMP)
                    """, (scan_id, case_id, target_json, depth))
            await asyncio.to_thread(_sync_create_scan)

        return scan_id

    async def update_scan_progress(
        self,
        scan_id: str,
        status: str = "completed",
        progress_percent: int = 100
    ) -> None:
        """Updates scan progress and completion status."""
        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE scans
                    SET status = $2, finished_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, scan_id, status)
        else:
            def _sync_update_scan():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.execute("""
                        UPDATE scans
                        SET status = ?, progress_percent = ?, finished_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (status, progress_percent, scan_id))
            await asyncio.to_thread(_sync_update_scan)

    async def list_scans(self, case_id: str) -> List[Dict[str, Any]]:
        """Lists scan history records for a case."""
        if self.engine_type == "postgres" and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM scans WHERE case_id = $1 ORDER BY started_at DESC", case_id)
                return [
                    {
                        "id": r["id"],
                        "case_id": r["case_id"],
                        "targets": json.loads(r["targets_input"]) if isinstance(r["targets_input"], str) else r["targets_input"],
                        "depth": r["depth"],
                        "status": r["status"],
                        "started_at": r["started_at"].isoformat() if hasattr(r["started_at"], "isoformat") else str(r["started_at"]),
                        "finished_at": r["finished_at"].isoformat() if r["finished_at"] and hasattr(r["finished_at"], "isoformat") else str(r["finished_at"])
                    }
                    for r in rows
                ]
        else:
            def _sync_list_scans():
                import sqlite3
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute("SELECT * FROM scans WHERE case_id = ? ORDER BY started_at DESC", (case_id,)).fetchall()
                    return [
                        {
                            "id": r["id"],
                            "case_id": r["case_id"],
                            "targets": json.loads(r["targets_input"] or "[]"),
                            "depth": r["depth"],
                            "status": r["status"],
                            "started_at": str(r["started_at"]),
                            "finished_at": str(r["finished_at"]) if r["finished_at"] else None
                        }
                        for r in rows
                    ]
            return await asyncio.to_thread(_sync_list_scans)


# Global singleton instance
GLOBAL_DB = DatabaseManager()
