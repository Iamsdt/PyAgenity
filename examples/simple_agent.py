"""
Simple example agent for testing PyAgenity platform.
"""

from typing import Any
from uuid import uuid4

from pyagenity.graph.checkpointer import InMemoryCheckpointer
from pyagenity.graph.graph.state_graph import StateGraph
from pyagenity.graph.state.agent_state import AgentState
from pyagenity.graph.utils import Message
from pyagenity.graph.utils.constants import END


def simple_agent_node(
    state: AgentState,
    config: dict[str, Any],
    checkpointer: Any | None = None,
    store: Any | None = None,
) -> AgentState:
    """Simple agent node that responds to messages."""
    context = state.context or []

    if context:
        last_message = context[-1]
        response_content = f"Echo: {last_message.content}"

        # Create response message
        response = Message(message_id=str(uuid4()), content=response_content, role="assistant")
        context.append(response)
    else:
        # Default message if no context
        response = Message(
            message_id=str(uuid4()), content="Hello! I'm a simple echo agent.", role="assistant"
        )
        context.append(response)

    return AgentState(context=context)


# Should we continue or end?
def should_continue(state: AgentState) -> str:
    """Determine if we should continue or end."""
    return END


# Create the graph
graph = StateGraph()
graph.add_node("agent", simple_agent_node)
graph.add_conditional_edges("agent", should_continue, {END: END})
graph.set_entry_point("agent")

# Compile the graph
app = graph.compile(checkpointer=InMemoryCheckpointer())

# Create a checkpointer for the server
checkpointer = InMemoryCheckpointer()
