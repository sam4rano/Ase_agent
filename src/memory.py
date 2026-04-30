"""
src/memory.py

Lightweight State & Memory Management for Àṣẹ Agent.
Uses SQLite to store recent interactions and provide context for the LLM.
"""

import sqlite3
import json
import os

class AgentMemory:
    def __init__(self, db_path="memory.db"):
        # Store in project root or app data dir, for now project root
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interaction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_input TEXT,
                    parsed_commands TEXT,
                    execution_results TEXT
                )
            ''')
            conn.commit()

    def add_interaction(self, user_input: str, parsed_commands: list, execution_results: list):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO interaction_log (user_input, parsed_commands, execution_results)
                VALUES (?, ?, ?)
            ''', (user_input, json.dumps(parsed_commands), json.dumps(execution_results)))
            conn.commit()

    def get_recent_context(self, limit=3) -> str:
        """Returns a string representation of recent interactions to use in LLM prompt."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_input, parsed_commands, execution_results
                FROM interaction_log
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            
        if not rows:
            return "No previous context."
            
        context = "Recent conversation and action history:\n"
        # Reverse to get chronological order (oldest to newest)
        for row in reversed(rows):
            user_input, parsed_commands, execution_results = row
            context += f"User said: {user_input}\n"
            context += f"Agent parsed actions: {parsed_commands}\n"
            context += f"System execution results: {execution_results}\n"
        return context
