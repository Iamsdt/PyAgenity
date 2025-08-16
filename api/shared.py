"""
Shared utilities for the PyAgenity API.
"""

from typing import Any

from fastapi import HTTPException

from pyagenity.graph.graph.compiled_graph import CompiledGraph


# Global variables for app state (will be set by server.py)
app_config: dict[str, Any] = {}
compiled_graphs: dict[str, CompiledGraph] = {}
checkpointers: dict[str, Any] = {}


def get_app_config() -> dict[str, Any]:
    """Get the current application configuration."""
    return app_config


def get_compiled_graph(graph_id: str = "agent") -> CompiledGraph:
    """Get a compiled graph by ID."""
    if graph_id not in compiled_graphs:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found")
    return compiled_graphs[graph_id]


def get_checkpointer(checkpointer_id: str = "default") -> Any:
    """Get a checkpointer by ID."""
    if checkpointer_id not in checkpointers:
        raise HTTPException(status_code=404, detail=f"Checkpointer '{checkpointer_id}' not found")
    return checkpointers[checkpointer_id]
