#!/usr/bin/env python3
"""
PyAgenity CLI - Command-line interface for building and deploying PyAgenity agents.

This CLI tool is similar to LangGraph CLI, allowing users to build Docker images
from their agent code and configuration files.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


import click
import typer
from dotenv import load_dotenv
import threading


def load_config(config_path: str = "pyagentic.json") -> dict[str, Any]:
    """Load configuration from pyagentic.json file."""
    config_file = Path(config_path)
    if not config_file.exists():
        raise click.ClickException(f"Configuration file {config_path} not found")

    with config_file.open() as f:
        return json.load(f)


def validate_config(config: dict[str, Any]) -> None:
    """Validate the configuration file structure."""
    required_fields = ["dependencies", "graphs"]

    for field in required_fields:
        if field not in config:
            raise click.ClickException(f"Missing required field '{field}' in configuration")

    if not config["graphs"]:
        raise click.ClickException("No graphs defined in configuration")

    # Validate graph paths exist
    for graph_id, graph_path in config["graphs"].items():
        if ":" not in graph_path:
            raise click.ClickException(f"Invalid graph path format for '{graph_id}': {graph_path}")

        module_path, _ = graph_path.split(":", 1)
        if not Path(module_path).exists():
            raise click.ClickException(f"Graph module not found: {module_path}")


def generate_dockerfile(config: dict[str, Any]) -> str:
    """Generate Dockerfile content based on configuration."""
    dependencies = config.get("dependencies", ["."])
    dockerfile_lines = config.get("dockerfile_lines", [])

    # Base Dockerfile template
    dockerfile_content = """# Generated Dockerfile for PyAgenity deployment
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install application dependencies
"""

    # Add dependency installation commands
    for dep in dependencies:
        if dep == ".":
            dockerfile_content += "RUN pip install -e .\n"
        elif dep.endswith(".txt"):
            dockerfile_content += f"RUN pip install -r {dep}\n"
        else:
            dockerfile_content += f"RUN pip install {dep}\n"

    # Add custom dockerfile lines
    if dockerfile_lines:
        dockerfile_content += "\n# Custom dockerfile lines\n"
        for line in dockerfile_lines:
            dockerfile_content += f"{line}\n"

    # Add server startup
    dockerfile_content += """
# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

# Start the server
CMD ["python", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
"""

    return dockerfile_content


def generate_requirements(config: dict[str, Any]) -> str:
    """Generate requirements.txt content."""
    base_requirements = [
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.20.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
    ]

    # Add PyAgenity as a dependency
    if "." not in config.get("dependencies", []):
        base_requirements.append("pyagenity>=0.1.0")

    return "\n".join(base_requirements)


def run_docker_build(image_tag: str, dockerfile_path: str, context_path: str) -> None:
    """Run docker build command."""
    cmd = ["docker", "build", "-t", image_tag, "-f", dockerfile_path, context_path]

    click.echo(f"Building Docker image: {image_tag}")
    click.echo(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        click.echo("✅ Docker image built successfully!")
        if result.stdout:
            click.echo(result.stdout)
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Docker build failed: {e}")
        if e.stderr:
            click.echo(f"Error: {e.stderr}")
        sys.exit(1)


@click.group()
@click.version_option(version="1.0.0", prog_name="pyagentic")




# --- Click CLI commands ---
@click.command()
@click.option("-t", "--tag", required=True, help="Docker image tag (e.g., my-agent:latest)")
@click.option(
    "-c",
    "--config",
    default="pyagentic.json",
    help="Path to configuration file (default: pyagentic.json)",
)
@click.option("--no-cache", is_flag=True, help="Build without using cache")
def build(tag: str, config: str, no_cache: bool):
    ... # existing build function body

@click.command()
@click.option(
    "-c",
    "--config",
    default="pyagentic.json",
    help="Path to configuration file (default: pyagentic.json)",
)
def validate(config: str):
    ... # existing validate function body

@click.command()
@click.option("--name", default="my-agent", help="Project name (default: my-agent)")
@click.option(
    "--dir",
    "directory",
    default=".",
    help="Directory to create project in (default: current directory)",
)
def init(name: str, directory: str):
    ... # existing init function body

# --- Click CLI group ---
@click.group()
@click.version_option(version="1.0.0", prog_name="pyagentic")
def cli():
    """PyAgenity CLI - Build and deploy PyAgenity agents."""
    pass

cli.add_command(build)
cli.add_command(validate)
cli.add_command(init)

# --- Typer integration and new commands ---
app = typer.Typer(help="PyAgenity CLI - Build, run, and deploy PyAgenity agents.")
app.add_typer(typer.main.get_command(cli), name="legacy", help="Legacy Click commands")

@app.command()
def api(
    host: str = typer.Option("127.0.0.1", help="Host to bind (default: 127.0.0.1)"),
    port: int = typer.Option(8000, help="Port to bind (default: 8000)"),
    reload: bool = typer.Option(True, help="Enable auto-reload (dev mode)")
):
    """Start the API server in dev mode using uvicorn."""
    import subprocess
    typer.echo(f"Starting API server at http://{host}:{port} (reload={reload})...")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.server:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")
    subprocess.run(cmd)

@app.command()
def run(
    host: str = typer.Option("127.0.0.1", help="Host to bind API (default: 127.0.0.1)"),
    port: int = typer.Option(8000, help="Port to bind API (default: 8000)"),
    react_dir: str = typer.Option("ui/app", help="Path to React app directory (default: ui/app)")
):
    """Start the API server and React app for development."""
    import subprocess

    def start_api():
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "api.server:app",
            "--host",
            host,
            "--port",
            str(port),
            "--reload",
        ]
        typer.echo(f"[API] Starting at http://{host}:{port} ...")
        subprocess.run(cmd)

    def start_react():
        typer.echo(f"[React] Starting dev server in {react_dir} ...")
        subprocess.run(["npm", "install"], cwd=react_dir)
        subprocess.run(["npm", "run", "dev"], cwd=react_dir)

    api_thread = threading.Thread(target=start_api)
    react_thread = threading.Thread(target=start_react)

    api_thread.start()
    react_thread.start()

    api_thread.join()
    react_thread.join()


if __name__ == "__main__":
    app()


@cli.command()
@click.option("-t", "--tag", required=True, help="Docker image tag (e.g., my-agent:latest)")
@click.option(
    "-c",
    "--config",
    default="pyagentic.json",
    help="Path to configuration file (default: pyagentic.json)",
)
@click.option("--no-cache", is_flag=True, help="Build without using cache")
def build(tag: str, config: str, no_cache: bool):
    """Build a Docker image from PyAgenity configuration."""
    try:
        # Load and validate configuration
        click.echo(f"Loading configuration from {config}...")
        app_config = load_config(config)
        validate_config(app_config)

        # Create build directory
        build_dir = Path(".pyagentic-build")
        build_dir.mkdir(exist_ok=True)

        # Generate Dockerfile
        click.echo("Generating Dockerfile...")
        dockerfile_content = generate_dockerfile(app_config)
        dockerfile_path = build_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)

        # Generate requirements.txt
        click.echo("Generating requirements.txt...")
        requirements_content = generate_requirements(app_config)
        requirements_path = build_dir / "requirements.txt"
        requirements_path.write_text(requirements_content)

        # Copy configuration file
        config_dest = build_dir / "pyagentic.json"
        config_dest.write_text(json.dumps(app_config, indent=2))

        # Load environment variables if specified
        env_config = app_config.get("env")
        if isinstance(env_config, str) and Path(env_config).exists():
            load_dotenv(env_config)
            click.echo(f"Loaded environment variables from {env_config}")

        # Build Docker image
        docker_cmd = [
            "docker",
            "build",
            "-t",
            tag,
            "-f",
            str(dockerfile_path),
        ]

        if no_cache:
            docker_cmd.append("--no-cache")

        docker_cmd.append(".")

        click.echo(f"Building Docker image: {tag}")
        result = subprocess.run(docker_cmd, check=True)

        if result.returncode == 0:
            click.echo("✅ Docker image built successfully!")
            click.echo(f"Image tag: {tag}")
            click.echo("\nTo run the container:")
            click.echo(f"  docker run -p 8000:8000 {tag}")

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Build failed: {e}") from e


@cli.command()
@click.option(
    "-c",
    "--config",
    default="pyagentic.json",
    help="Path to configuration file (default: pyagentic.json)",
)
def validate(config: str):
    """Validate PyAgenity configuration file."""
    try:
        click.echo(f"Validating configuration file: {config}")
        app_config = load_config(config)
        validate_config(app_config)
        click.echo("✅ Configuration is valid!")

        # Show configuration summary
        click.echo("\nConfiguration summary:")
        click.echo(f"  Graphs: {list(app_config['graphs'].keys())}")
        click.echo(f"  Dependencies: {app_config.get('dependencies', [])}")

        auth_config = app_config.get("auth")
        if auth_config:
            click.echo(
                f"  Authentication: {auth_config.get('type', 'none')} ({auth_config.get('backend', 'none')})"
            )
        else:
            click.echo("  Authentication: disabled")

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Validation failed: {e}") from e


@cli.command()
@click.option("--name", default="my-agent", help="Project name (default: my-agent)")
@click.option(
    "--dir",
    "directory",
    default=".",
    help="Directory to create project in (default: current directory)",
)
def init(name: str, directory: str):
    """Initialize a new PyAgenity project."""
    project_dir = Path(directory) / name

    try:
        # Create project directory
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create basic project structure
        (project_dir / "agents").mkdir(exist_ok=True)

        # Create sample agent file
        agent_content = '''"""
Sample PyAgenity agent.
"""

from dotenv import load_dotenv
from pyagenity.graph.checkpointer import InMemoryCheckpointer
from pyagenity.graph.graph.state_graph import StateGraph
from pyagenity.graph.state.agent_state import AgentState

load_dotenv()

checkpointer = InMemoryCheckpointer()


def sample_agent(state: AgentState, config: dict, checkpointer=None, store=None):
    """Sample agent function."""
    # Add your agent logic here
    return {"message": "Hello from PyAgenity agent!"}


# Create graph
graph = StateGraph()
graph.add_node("agent", sample_agent)
graph.set_entry_point("agent")

# Compile graph
app = graph.compile(checkpointer=checkpointer)
'''

        agent_file = project_dir / "agents" / "sample_agent.py"
        agent_file.write_text(agent_content)

        # Create configuration file
        config_content = {
            "dependencies": ["."],
            "graphs": {"agent": "./agents/sample_agent.py:app"},
            "env": ".env",
            "auth": None,
        }

        config_file = project_dir / "pyagentic.json"
        config_file.write_text(json.dumps(config_content, indent=2))

        # Create .env file
        env_file = project_dir / ".env"
        env_file.write_text("# Environment variables\n# Add your API keys and configuration here\n")

        # Create requirements.txt
        requirements_file = project_dir / "requirements.txt"
        requirements_file.write_text("pyagenity>=0.1.0\npython-dotenv>=1.0.0\n")

        click.echo(f"✅ Project '{name}' initialized successfully!")
        click.echo(f"📁 Project directory: {project_dir}")
        click.echo("\nNext steps:")
        click.echo(f"  cd {project_dir}")
        click.echo("  pip install -r requirements.txt")
        click.echo("  pyagentic validate")
        click.echo("  pyagentic build -t my-agent:latest")

    except Exception as e:
        raise click.ClickException(f"Project initialization failed: {e}") from e



# --- New Typer commands ---

@app.command()
def api(
    host: str = typer.Option("127.0.0.1", help="Host to bind (default: 127.0.0.1)"),
    port: int = typer.Option(8000, help="Port to bind (default: 8000)"),
    reload: bool = typer.Option(True, help="Enable auto-reload (dev mode)")
):
    """Start the API server in dev mode using uvicorn."""
    import subprocess
app.add_typer(typer.main.get_command(cli), name="legacy", help="Legacy Click commands")

@app.command()
    typer.echo(f"Starting API server at http://{host}:{port} (reload={reload})...")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.server:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")
    subprocess.run(cmd)


            # --- New Typer commands ---

@app.command()
def run(
    host: str = typer.Option("127.0.0.1", help="Host to bind API (default: 127.0.0.1)"),
    port: int = typer.Option(8000, help="Port to bind API (default: 8000)"),
    react_dir: str = typer.Option("ui/app", help="Path to React app directory (default: ui/app)")
):
    """Start the API server and React app for development."""
    import subprocess

    def start_api():
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "api.server:app",
            "--host",
            host,
            "--port",
            str(port),
            "--reload",
        ]
        typer.echo(f"[API] Starting at http://{host}:{port} ...")
            app()

    def start_react():
        typer.echo(f"[React] Starting dev server in {react_dir} ...")
        subprocess.run(["npm", "install"], cwd=react_dir)
        subprocess.run(["npm", "run", "dev"], cwd=react_dir)

    api_thread = threading.Thread(target=start_api)
    react_thread = threading.Thread(target=start_react)

    api_thread.start()
    react_thread.start()

    api_thread.join()
    react_thread.join()


if __name__ == "__main__":
    app()
