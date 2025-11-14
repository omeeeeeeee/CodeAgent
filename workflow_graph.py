"""LangGraph workflow based on JSON instructions.

Creates a blank template for Windows automation workflows.
"""

from __future__ import annotations

import json
from typing import Union, Dict, Any, Optional, Tuple
from pydantic import BaseModel
import asyncio
import logging

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from cuteagent import WindowsAgent  # type: ignore

# =============================================================================
# STATE DEFINITION
# =============================================================================

class State(BaseModel):
    """Input state for the agent."""
    user_input: Union[str, Dict[str, Any], None] = None
    current_node: int = 0
    status: str = "Ongoing"
    # Add your custom state variables here based on your workflow needs

# =============================================================================
# CONFIGURATION
# =============================================================================

# OS URL - update this to point to your Windows server
OS_URL = "https://fintor-ec2-dev.ngrok.app"

# =============================================================================
# ACTION FUNCTIONS
# These are reusable building blocks for creating your workflow nodes
# =============================================================================

async def click_action(x: int, y: int, description: str, node_number: int, state: State) -> State:
    """Generic click action function."""
    agent = WindowsAgent(os_url=OS_URL)
    try:
        await asyncio.to_thread(agent.click_element, x, y)
        logging.info(f"Node {node_number}: Successfully clicked at ({x}, {y}) - {description}")
        status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error clicking at ({x}, {y}) - {description}: {e}")
        status = "Error"
    
    state.current_node = node_number
    state.status = status
    return state

async def wait_action(duration: int, description: str, node_number: int, state: State) -> State:
    """Generic wait action function."""
    try:
        await asyncio.sleep(duration)
        logging.info(f"Node {node_number}: Successfully waited {duration} seconds - {description}")
        status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error during wait - {description}: {e}")
        status = "Error"
    
    state.current_node = node_number
    state.status = status
    return state

async def input_action(text: str, description: str, node_number: int, state: State) -> State:
    """Generic input action function."""
    agent = WindowsAgent(os_url=OS_URL)
    try:
        # For INPUT action, use the correct format
        input_type = {
            "action": "INPUT",
            "coordinate": [0, 0], 
            "value": text, 
            "model_selected": "claude"
        }
        await asyncio.to_thread(agent.act, input_type)
        logging.info(f"Node {node_number}: Successfully input text '{text}' - {description}")
        status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error inputting text - {description}: {e}")
        status = "Error"
    
    state.current_node = node_number
    state.status = status
    return state

async def enter_action(description: str, node_number: int, state: State) -> State:
    """Generic enter key action function."""
    agent = WindowsAgent(os_url=OS_URL)
    try:
        # For ENTER action, use the act method with ENTER action
        input_data = {
            "action": "ENTER",
            "coordinate": [0, 0],
            "value": "",
            "model_selected": "claude"
        }
        await asyncio.to_thread(agent.act, input_data)
        logging.info(f"Node {node_number}: Successfully pressed ENTER - {description}")
        status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error pressing ENTER - {description}: {e}")
        status = "Error"
    
    state.current_node = node_number
    state.status = status
    return state

async def double_click_action(x: int, y: int, description: str, node_number: int, state: State) -> State:
    """Generic double-click action function."""
    agent = WindowsAgent(os_url=OS_URL)
    try:
        # Use the correct DOUBLE-CLICK action format
        input_type = {
            "action": "DOUBLE-CLICK",
            "coordinate": [x, y], 
            "value": "value", 
            "model_selected": "claude"
        }
        await asyncio.to_thread(agent.act, input_type)
        logging.info(f"Node {node_number}: Successfully double-clicked at ({x}, {y}) - {description}")
        status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error double-clicking at ({x}, {y}) - {description}: {e}")
        status = "Error"
    
    state.current_node = node_number
    state.status = status
    return state

async def screenshot_action(description: str, node_number: int, state: State) -> Tuple[State, Optional[str]]:
    """Generic screenshot action function. Returns (state, screenshot_url)."""
    agent = WindowsAgent(os_url=OS_URL)
    screenshot_url = None
    
    try:
        screenshot_result = await asyncio.to_thread(agent.screenshot)
        
        if isinstance(screenshot_result, dict) and "url" in screenshot_result:
            screenshot_url = screenshot_result["url"]
            logging.info(f"Node {node_number}: Screenshot captured: {screenshot_url} - {description}")
        elif isinstance(screenshot_result, str):
            screenshot_url = screenshot_result
            logging.info(f"Node {node_number}: Screenshot captured: {screenshot_url} - {description}")
        elif isinstance(screenshot_result, bytes):
            import base64
            base64_str = base64.b64encode(screenshot_result).decode('utf-8')
            screenshot_url = f"data:image/png;base64,{base64_str}"
            logging.info(f"Node {node_number}: Screenshot captured as data URI - {description}")
        else:
            logging.warning(f"Node {node_number}: Unexpected screenshot result format: {type(screenshot_result)} - {description}")
            screenshot_url = None
        
        status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error taking screenshot - {description}: {e}")
        status = "Error"
        screenshot_url = None
    
    state.current_node = node_number
    state.status = status
    return state, screenshot_url

# =============================================================================
# WORKFLOW NODES
# Add your custom workflow nodes here using the action functions above
# =============================================================================

# Example workflow node - replace with your actual workflow
async def example_node(state: State, config: RunnableConfig) -> State:
    """Example node showing how to use action functions - replace with your workflow."""
    return await click_action(200, 100, "Example click", 1, state)

# Example screenshot node - shows how to use screenshot_action
async def example_screenshot_node(state: State, config: RunnableConfig) -> State:
    """Example showing how to use screenshot_action - replace with your workflow."""
    state, screenshot_url = await screenshot_action("Example screenshot", 1, state)
    # You can now use screenshot_url in your workflow
    # For example, store it in a custom state field or process it further
    logging.info(f"Screenshot URL available: {screenshot_url}")
    return state

# =============================================================================
# GRAPH COMPILATION
# Define and compile your workflow graph here
# =============================================================================

# Define your graph here - customize as needed
graph = (
    StateGraph(State)
    .add_node("example_node", example_node)
    .add_edge("__start__", "example_node")
    .add_edge("example_node", "__end__")
    .compile(
        name="lgBlank",
    )
)