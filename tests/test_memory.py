"""
tests/test_memory.py — Unit tests for AgentMemory.

Run: python3 -m pytest tests/test_memory.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.memory import AgentMemory


@pytest.fixture
def memory(tmp_path):
    """AgentMemory using a temp database."""
    db = tmp_path / "test.db"
    return AgentMemory(db_path=str(db))


class TestAgentMemory:

    def test_empty_context(self, memory):
        result = memory.get_recent_context()
        assert result == "No previous context."

    def test_add_and_retrieve(self, memory):
        memory.add_interaction("open youtube", [{"action": "open_website"}], ["ok:done"])
        ctx = memory.get_recent_context()
        assert "open youtube" in ctx
        assert "open_website" in ctx

    def test_context_limit(self, memory):
        for i in range(10):
            memory.add_interaction(f"command {i}", [{"action": "test"}], [f"ok:{i}"])
        ctx = memory.get_recent_context(limit=3)
        # Should contain only the 3 most recent
        assert "command 9" in ctx
        assert "command 7" in ctx
        assert "command 0" not in ctx

    def test_chronological_order(self, memory):
        memory.add_interaction("first", [], [])
        memory.add_interaction("second", [], [])
        ctx = memory.get_recent_context(limit=2)
        # Should be oldest-first in the context string
        assert ctx.index("first") < ctx.index("second")

    def test_pruning_keeps_max_100(self, memory):
        for i in range(110):
            memory.add_interaction(f"cmd {i}", [], [])
        # Check row count
        import sqlite3
        with sqlite3.connect(memory.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM interaction_log").fetchone()[0]
        assert count <= 100
