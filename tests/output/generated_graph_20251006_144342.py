"""LangGraph workflow based on JSON instructions.

Creates a workflow for Windows automation based on user interaction events.
"""

from __future__ import annotations

import json
from typing import Union, Dict, Any, Optional
from pydantic import BaseModel
import asyncio
import logging
import base64

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

# =============================================================================
# CONFIGURATION
# =============================================================================

GRAPH_NAME = "lgGraph"
OS_URL = "https://fintor-dev-recording.ngrok.app"

# =============================================================================
# STATE DEFINITION
# =============================================================================

class State(BaseModel):
    """Input state for the agent."""
    user_input: Union[str, Dict[str, Any], None] = None
    current_node: int = 0
    status: str = ""
    has_error: bool = False
    screenshot_url: Optional[str] = None

# =============================================================================
# AGENT INTEGRATION LAYER
# =============================================================================

class _BaseAgent:
    async def click(self, x: int, y: int) -> None: ...
    async def double_click(self, x: int, y: int) -> None: ...
    async def input_text(self, text: str) -> None: ...
    async def press_enter(self) -> None: ...
    async def screenshot(self) -> Union[str, bytes, Dict[str, Any]]: ...

class _SimAgent(_BaseAgent):
    async def click(self, x: int, y: int):
        logging.info(f"[SIM] click({x},{y})")
        await asyncio.sleep(0.05)
    
    async def double_click(self, x: int, y: int):
        logging.info(f"[SIM] double_click({x},{y})")
        await asyncio.sleep(0.08)
    
    async def input_text(self, text: str):
        logging.info(f"[SIM] input_text({text!r})")
        await asyncio.sleep(0.05)
    
    async def press_enter(self):
        logging.info("[SIM] press_enter()")
        await asyncio.sleep(0.03)
    
    async def screenshot(self):
        logging.info("[SIM] screenshot()")
        await asyncio.sleep(0.1)
        return "data:image/png;base64,placeholder"

class _WindowsAgentAdapter(_BaseAgent):
    def __init__(self, wa: Any):
        self._a = wa
    
    async def click(self, x: int, y: int):
        await asyncio.to_thread(self._a.click_element, x, y)
    
    async def double_click(self, x: int, y: int):
        payload = {"action": "DOUBLE-CLICK", "coordinate": [x, y], "value": "value", "model_selected": "claude"}
        await asyncio.to_thread(self._a.act, payload)
    
    async def input_text(self, text: str):
        payload = {"action": "INPUT", "coordinate": [0, 0], "value": text, "model_selected": "claude"}
        await asyncio.to_thread(self._a.act, payload)
    
    async def press_enter(self):
        payload = {"action": "ENTER", "coordinate": [0, 0], "value": "", "model_selected": "claude"}
        await asyncio.to_thread(self._a.act, payload)
    
    async def screenshot(self):
        return await asyncio.to_thread(self._a.screenshot)

def get_agent(os_url: Optional[str]) -> _BaseAgent:
    try:
        from cuteagent import WindowsAgent  # soft import
        logging.info("Using real WindowsAgent.")
        return _WindowsAgentAdapter(WindowsAgent(os_url=os_url))
    except Exception as e:
        logging.warning(f"Falling back to SimAgent (cuteagent unavailable): {e}")
        return _SimAgent()

AGENT: _BaseAgent = get_agent(OS_URL)

# =============================================================================
# ACTION FUNCTIONS
# =============================================================================

async def click_action(state: State, config: RunnableConfig, x: int, y: int, description: str, node_number: int) -> State:
    """Generic click action function."""
    try:
        await AGENT.click(x, y)
        logging.info(f"Node {node_number}: Successfully clicked at ({x}, {y}) - {description}")
        state.status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error clicking at ({x}, {y}) - {description}: {e}")
        state.status = "Error"
        state.has_error = True
    
    state.current_node = node_number
    return state

async def double_click_action(state: State, config: RunnableConfig, x: int, y: int, description: str, node_number: int) -> State:
    """Generic double-click action function."""
    try:
        await AGENT.double_click(x, y)
        logging.info(f"Node {node_number}: Successfully double-clicked at ({x}, {y}) - {description}")
        state.status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error double-clicking at ({x}, {y}) - {description}: {e}")
        state.status = "Error"
        state.has_error = True
    
    state.current_node = node_number
    return state

async def input_action(state: State, config: RunnableConfig, text: str, description: str, node_number: int) -> State:
    """Generic input action function."""
    try:
        await AGENT.input_text(text)
        logging.info(f"Node {node_number}: Successfully input text '{text}' - {description}")
        state.status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error inputting text - {description}: {e}")
        state.status = "Error"
        state.has_error = True
    
    state.current_node = node_number
    return state

async def enter_action(state: State, config: RunnableConfig, description: str, node_number: int) -> State:
    """Generic enter key action function."""
    try:
        await AGENT.press_enter()
        logging.info(f"Node {node_number}: Successfully pressed ENTER - {description}")
        state.status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error pressing ENTER - {description}: {e}")
        state.status = "Error"
        state.has_error = True
    
    state.current_node = node_number
    return state

async def wait_action(state: State, config: RunnableConfig, duration: int, description: str, node_number: int) -> State:
    """Generic wait action function."""
    try:
        await asyncio.sleep(duration)
        logging.info(f"Node {node_number}: Successfully waited {duration} seconds - {description}")
        state.status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error during wait - {description}: {e}")
        state.status = "Error"
        state.has_error = True
    
    state.current_node = node_number
    return state

async def screenshot_action(state: State, config: RunnableConfig, description: str, node_number: int) -> State:
    """Generic screenshot action function."""
    try:
        screenshot_result = await AGENT.screenshot()
        
        if isinstance(screenshot_result, dict) and "url" in screenshot_result:
            state.screenshot_url = screenshot_result["url"]
            logging.info(f"Node {node_number}: Screenshot captured: {state.screenshot_url} - {description}")
        elif isinstance(screenshot_result, str):
            state.screenshot_url = screenshot_result
            logging.info(f"Node {node_number}: Screenshot captured: {state.screenshot_url} - {description}")
        elif isinstance(screenshot_result, bytes):
            base64_str = base64.b64encode(screenshot_result).decode('utf-8')
            state.screenshot_url = f"data:image/png;base64,{base64_str}"
            logging.info(f"Node {node_number}: Screenshot captured as data URI - {description}")
        else:
            logging.warning(f"Node {node_number}: Unexpected screenshot result format: {type(screenshot_result)} - {description}")
            state.screenshot_url = None
        
        state.status = "Success"
    except Exception as e:
        logging.error(f"Node {node_number}: Error taking screenshot - {description}: {e}")
        state.status = "Error"
        state.has_error = True
        state.screenshot_url = None
    
    state.current_node = node_number
    return state

# =============================================================================
# WORKFLOW NODES
# =============================================================================

# Navigation phase nodes
async def node_1(state: State, config: RunnableConfig) -> State:
    """Click at (85, 60)"""
    return await click_action(state, config, 85, 60, "Initial click", 1)

async def node_2(state: State, config: RunnableConfig) -> State:
    """Click at (233, 234)"""
    return await click_action(state, config, 233, 234, "Click at field", 2)

async def node_3(state: State, config: RunnableConfig) -> State:
    """Input text 'DEFAULT_LOAN'"""
    return await input_action(state, config, "DEFAULT_LOAN", "Type DEFAULT_LOAN", 3)

async def node_4(state: State, config: RunnableConfig) -> State:
    """Press Enter"""
    return await enter_action(state, config, "Press Enter to confirm", 4)

async def node_5(state: State, config: RunnableConfig) -> State:
    """Click at (184, 254)"""
    return await click_action(state, config, 184, 254, "Click on result", 5)

async def node_6(state: State, config: RunnableConfig) -> State:
    """Double-click at (184, 254)"""
    return await double_click_action(state, config, 184, 254, "Double-click to open", 6)

# Main workflow nodes
async def node_7(state: State, config: RunnableConfig) -> State:
    """Click at (340, 36)"""
    return await click_action(state, config, 340, 36, "Navigate to menu", 7)

async def node_8(state: State, config: RunnableConfig) -> State:
    """Click at (391, 65)"""
    return await click_action(state, config, 391, 65, "Select menu option", 8)

async def node_9(state: State, config: RunnableConfig) -> State:
    """Click at (507, 266)"""
    return await click_action(state, config, 507, 266, "Click form field", 9)

async def node_10(state: State, config: RunnableConfig) -> State:
    """Click at (846, 545)"""
    return await click_action(state, config, 846, 545, "Click button", 10)

async def node_11(state: State, config: RunnableConfig) -> State:
    """Click at (859, 669)"""
    return await click_action(state, config, 859, 669, "Click next button", 11)

async def node_12(state: State, config: RunnableConfig) -> State:
    """Click at (134, 65)"""
    return await click_action(state, config, 134, 65, "Navigate back", 12)

async def node_13(state: State, config: RunnableConfig) -> State:
    """Click at (28, 438)"""
    return await click_action(state, config, 28, 438, "Click sidebar", 13)

async def node_14(state: State, config: RunnableConfig) -> State:
    """Click at (77, 540)"""
    return await click_action(state, config, 77, 540, "Click option", 14)

async def node_15(state: State, config: RunnableConfig) -> State:
    """Click at (1350, 541)"""
    return await click_action(state, config, 1350, 541, "Click right panel", 15)

async def node_16(state: State, config: RunnableConfig) -> State:
    """Click at (878, 313)"""
    return await click_action(state, config, 878, 313, "Click center area", 16)

async def node_17(state: State, config: RunnableConfig) -> State:
    """Click at (825, 598)"""
    return await click_action(state, config, 825, 598, "Click lower button", 17)

async def node_18(state: State, config: RunnableConfig) -> State:
    """Click at (765, 447)"""
    return await click_action(state, config, 765, 447, "Click form element", 18)

async def node_19(state: State, config: RunnableConfig) -> State:
    """Click at (1339, 97)"""
    return await click_action(state, config, 1339, 97, "Click top right", 19)

async def node_20(state: State, config: RunnableConfig) -> State:
    """Click at (743, 443)"""
    return await click_action(state, config, 743, 443, "Click nearby element", 20)

# Return phase nodes
async def node_21(state: State, config: RunnableConfig) -> State:
    """Click at (81, 60)"""
    return await click_action(state, config, 81, 60, "Return navigation", 21)

async def node_22(state: State, config: RunnableConfig) -> State:
    """Click at (327, 99)"""
    return await click_action(state, config, 327, 99, "Click menu item", 22)

async def node_23(state: State, config: RunnableConfig) -> State:
    """Click at (216, 117)"""
    return await click_action(state, config, 216, 117, "Select option", 23)

async def node_24(state: State, config: RunnableConfig) -> State:
    """Click at (23, 65)"""
    return await click_action(state, config, 23, 65, "Click home", 24)

async def node_25(state: State, config: RunnableConfig) -> State:
    """Click at (1284, 11)"""
    return await click_action(state, config, 1284, 11, "Close window", 25)

async def node_26(state: State, config: RunnableConfig) -> State:
    """Click at (124, 633)"""
    return await click_action(state, config, 124, 633, "Click terminal", 26)

async def node_27(state: State, config: RunnableConfig) -> State:
    """Click at (124, 633) again"""
    return await click_action(state, config, 124, 633, "Click terminal again", 27)

async def node_28(state: State, config: RunnableConfig) -> State:
    """Click at (723, 470)"""
    return await click_action(state, config, 723, 470, "Confirm stop recording", 28)

# =============================================================================
# SUBGRAPH BUILDERS
# =============================================================================

def build_navigation_subgraph():
    """Build navigation subgraph for initial steps."""
    g = StateGraph(State)
    g.add_node("node_1", node_1)
    g.add_node("node_2", node_2)
    g.add_node("node_3", node_3)
    g.add_node("node_4", node_4)
    g.add_node("node_5", node_5)
    g.add_node("node_6", node_6)
    
    g.add_edge("__start__", "node_1")
    g.add_edge("node_1", "node_2")
    g.add_edge("node_2", "node_3")
    g.add_edge("node_3", "node_4")
    g.add_edge("node_4", "node_5")
    g.add_edge("node_5", "node_6")
    g.add_edge("node_6", "__end__")
    
    return g.compile(name="navigation_subgraph")

def build_main_workflow():
    """Build main workflow subgraph for core task steps."""
    g = StateGraph(State)
    g.add_node("node_7", node_7)
    g.add_node("node_8", node_8)
    g.add_node("node_9", node_9)
    g.add_node("node_10", node_10)
    g.add_node("node_11", node_11)
    g.add_node("node_12", node_12)
    g.add_node("node_13", node_13)
    g.add_node("node_14", node_14)
    g.add_node("node_15", node_15)
    g.add_node("node_16", node_16)
    g.add_node("node_17", node_17)
    g.add_node("node_18", node_18)
    g.add_node("node_19", node_19)
    g.add_node("node_20", node_20)
    
    g.add_edge("__start__", "node_7")
    g.add_edge("node_7", "node_8")
    g.add_edge("node_8", "node_9")
    g.add_edge("node_9", "node_10")
    g.add_edge("node_10", "node_11")
    g.add_edge("node_11", "node_12")
    g.add_edge("node_12", "node_13")
    g.add_edge("node_13", "node_14")
    g.add_edge("node_14", "node_15")
    g.add_edge("node_15", "node_16")
    g.add_edge("node_16", "node_17")
    g.add_edge("node_17", "node_18")
    g.add_edge("node_18", "node_19")
    g.add_edge("node_19", "node_20")
    g.add_edge("node_20", "__end__")
    
    return g.compile(name="main_workflow")

def build_return_subgraph():
    """Build return subgraph for cleanup/return steps."""
    g = StateGraph(State)
    g.add_node("node_21", node_21)
    g.add_node("node_22", node_22)
    g.add_node("node_23", node_23)
    g.add_node("node_24", node_24)
    g.add_node("node_25", node_25)
    g.add_node("node_26", node_26)
    g.add_node("node_27", node_27)
    g.add_node("node_28", node_28)
    
    g.add_edge("__start__", "node_21")
    g.add_edge("node_21", "node_22")
    g.add_edge("node_22", "node_23")
    g.add_edge("node_23", "node_24")
    g.add_edge("node_24", "node_25")
    g.add_edge("node_25", "node_26")
    g.add_edge("node_26", "node_27")
    g.add_edge("node_27", "node_28")
    g.add_edge("node_28", "__end__")
    
    return g.compile(name="return_subgraph")

# =============================================================================
# FINALIZER
# =============================================================================

async def finalize_state(state: State, config: RunnableConfig) -> State:
    """Finalize the workflow state."""
    state.status = "Error" if state.has_error else "Completed"
    return state

# =============================================================================
# MAIN GRAPH
# =============================================================================

def build_main_graph():
    """Build and compile the main graph with subgraphs."""
    navigation_subgraph = build_navigation_subgraph()
    main_workflow = build_main_workflow()
    return_subgraph = build_return_subgraph()
    
    g = StateGraph(State)
    g.add_node("navigation_subgraph", navigation_subgraph)
    g.add_node("main_workflow", main_workflow)
    g.add_node("return_subgraph", return_subgraph)
    g.add_node("finalize_state", finalize_state)
    
    g.add_edge("__start__", "navigation_subgraph")
    g.add_edge("navigation_subgraph", "main_workflow")
    g.add_edge("main_workflow", "return_subgraph")
    g.add_edge("return_subgraph", "finalize_state")
    g.add_edge("finalize_state", "__end__")
    
    return g.compile(name=GRAPH_NAME)

graph = build_main_graph()