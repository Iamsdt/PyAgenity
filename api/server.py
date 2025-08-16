import json
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pyagenity.graph.checkpointer import InMemoryCheckpointer
from pyagenity.graph.graph.compiled_graph import CompiledGraph

from .auth import init_auth_config
from .routes import auth_router, messages_router, state_router, threads_router
from .shared import app_config, checkpointers, compiled_graphs


def load_config_from_file(config_path: str = "pyagentic.json") -> dict[str, Any]:
    """Load configuration from pyagentic.json file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file {config_path} not found")

    with open(config_path) as f:
        return json.load(f)


def load_graph_from_module(graph_path: str) -> CompiledGraph:
    """Load a compiled graph from a module path."""
    import importlib.util
    import sys

    # Parse module path (e.g., "./examples/react/react_weather_agent.py:app")
    module_path, graph_name = graph_path.split(":")

    # Load the module
    spec = importlib.util.spec_from_file_location("agent_module", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_module"] = module
    spec.loader.exec_module(module)

    # Get the graph object
    graph = getattr(module, graph_name)
    if not isinstance(graph, CompiledGraph):
        raise TypeError(f"Expected CompiledGraph, got {type(graph)}")

    return graph


def load_checkpointer_from_module(checkpointer_path: str) -> Any:
    """Load a checkpointer from a module path."""
    import importlib.util
    import sys

    # Parse module path (e.g., "./examples/react/react_weather_agent.py:checkpointer")
    module_path, checkpointer_name = checkpointer_path.split(":")

    # Load the module
    spec = importlib.util.spec_from_file_location("checkpointer_module", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["checkpointer_module"] = module
    spec.loader.exec_module(module)

    # Get the checkpointer object
    return getattr(module, checkpointer_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup

    # Load configuration
    config_path = os.getenv("PYAGENTIC_CONFIG", "pyagentic.json")
    try:
        app_config.update(load_config_from_file(config_path))
    except FileNotFoundError:
        print(f"Warning: {config_path} not found, using default configuration")
        app_config.update(
            {
                "dependencies": ["."],
                "graphs": {},
                "env": {},
                "auth": None,
            }
        )

    # Initialize authentication
    auth_config = app_config.get("auth")
    init_auth_config(auth_config)

    # Load graphs
    graphs_config = app_config.get("graphs", {})
    for graph_id, graph_path in graphs_config.items():
        try:
            compiled_graphs[graph_id] = load_graph_from_module(graph_path)
            print(f"Loaded graph: {graph_id}")
        except Exception as e:
            print(f"Failed to load graph {graph_id}: {e}")

    # Load checkpointers
    checkpointer_path = app_config.get("checkpointer")
    if checkpointer_path:
        try:
            default_checkpointer = load_checkpointer_from_module(checkpointer_path)
            checkpointers["default"] = default_checkpointer
            print("Loaded custom checkpointer")
        except Exception as e:
            print(f"Failed to load checkpointer: {e}")
            checkpointers["default"] = InMemoryCheckpointer()
    else:
        checkpointers["default"] = InMemoryCheckpointer()

    # Load environment variables
    env_config = app_config.get("env", {})
    if isinstance(env_config, str):
        # Load from .env file
        from dotenv import load_dotenv

        load_dotenv(env_config)
    elif isinstance(env_config, dict):
        # Set from dict
        for key, value in env_config.items():
            os.environ[key] = str(value)

    print("PyAgenity API server startup complete")

    yield

    # Shutdown
    print("PyAgenity API server shutdown")


# Create FastAPI app
app = FastAPI(
    title="PyAgenity API",
    description="REST API for PyAgenity agent framework deployment",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/v1", tags=["auth"])
app.include_router(threads_router, prefix="/v1", tags=["threads"])
app.include_router(messages_router, prefix="/v1", tags=["messages"])
app.include_router(state_router, prefix="/v1", tags=["state"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "PyAgenity API Server", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "graphs": list(compiled_graphs.keys())}


@app.get("/ok")
async def ok_check():
    """Simple ok check (LangGraph compatibility)."""
    return {"ok": True}
