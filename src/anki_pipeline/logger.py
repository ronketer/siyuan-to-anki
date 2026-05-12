"""Structured logging for the Anki Pipeline.

Provides production-grade observability by logging every agent interaction,
tool call, and decision to a timestamped JSON file. This enables:
- Debugging: Trace exactly what each agent did and why
- Auditing: Verify the decision path before cards were written to Anki
- Portfolio: Demonstrate production-aware design patterns
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class PipelineLogger:
    """Logs pipeline execution to JSON for observability and debugging."""

    def __init__(self, run_id: Optional[str] = None):
        """Initialize logger for a pipeline run.

        Args:
            run_id: Optional custom run ID. If None, uses timestamp.
        """
        self.run_id = run_id or datetime.now().isoformat().replace(":", "-")
        self.log_dir = Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = self.log_dir / f"{self.run_id}.json"
        self.entries: list[dict[str, Any]] = []

        # Track rejection count for guardrail visibility
        self.rejection_count = 0
        self.max_rejections = 2

    def log_agent_message(
        self,
        agent_name: str,
        content: str,
        message_type: str = "message",
    ) -> None:
        """Log an agent's message or action.

        Args:
            agent_name: Name of the agent that spoke
            content: The message content
            message_type: 'message', 'approval', 'rejection', etc.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "type": message_type,
            "content": content,
        }
        self.entries.append(entry)

    def log_tool_call(
        self,
        agent_name: str,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_result: str,
    ) -> None:
        """Log a tool invocation by an agent.

        Args:
            agent_name: Agent that called the tool
            tool_name: Name of the tool (e.g., 'fetch_siyuan_notes')
            tool_input: Arguments passed to the tool
            tool_result: String result from the tool
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "type": "tool_call",
            "tool": tool_name,
            "input": tool_input,
            "result": tool_result,
        }
        self.entries.append(entry)

    def log_rejection(self, agent_name: str, reason: str = "") -> None:
        """Log a card rejection and increment the rejection counter.

        Args:
            agent_name: Name of the agent that performed the rejection
            reason: Optional explanation for the rejection
        """
        self.rejection_count += 1
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "type": "rejection",
            "rejection_count": self.rejection_count,
            "reason": reason,
            "guardrail_active": self.rejection_count >= self.max_rejections,
        }
        self.entries.append(entry)

    def log_approval(self, card_count: int = 0) -> None:
        """Log human approval of cards.

        Args:
            card_count: Number of cards approved
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "approval",
            "card_count": card_count,
        }
        self.entries.append(entry)

    def log_outcome(self, outcome: str, saved_cards: int = 0) -> None:
        """Log the final outcome of the pipeline run.

        Args:
            outcome: 'success', 'cancelled', 'error', etc.
            saved_cards: Number of cards successfully saved to Anki
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "outcome",
            "result": outcome,
            "saved_cards": saved_cards,
            "total_rejections": self.rejection_count,
            "total_messages": len(self.entries),
        }
        self.entries.append(entry)

    def save(self) -> Path:
        """Persist the log to disk.

        Returns:
            Path to the written log file
        """
        # Add metadata
        log_data = {
            "run_id": self.run_id,
            "started": self.entries[0]["timestamp"] if self.entries else None,
            "ended": datetime.now().isoformat(),
            "entries": self.entries,
        }

        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        return self.log_file

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the logged run.

        Returns:
            Dictionary with run stats
        """
        return {
            "run_id": self.run_id,
            "total_entries": len(self.entries),
            "rejections": self.rejection_count,
            "log_file": str(self.log_file),
        }
