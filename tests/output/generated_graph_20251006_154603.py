from __future__ import annotations

import json
import asyncio
import logging
import base64
from typing import Union, Dict, Any, Optional
from pydantic import BaseModel
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

# =============================================================================
# CONFIGURATION
# =============================================================================

GRAPH_NAME = "encompass_workflow"
OS_URL = "https://fintor-dev-recording.ngrok.app"

# =============================================================================
# STATE DEFINITION
# =============================================================================

class State(BaseModel):
    """State for the Encompass workflow."""
    user_input: Union[str, Dict[str, Any], None] = None
    current_node: int = 0
    status: str = ""
    has_error: bool = False
    screenshot_url: Optional[str] = None
    typed_text: str = ""

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
# ACTION HELPERS
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
        # Handle state field references
        if text.startswith("state."):
            field_name = text[6:]  # Remove "state."
            text = str(getattr(state, field_name, ""))
        
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
        elif isinstance(screenshot_result, str):
            state.screenshot_url = screenshot_result
        elif isinstance(screenshot_result, bytes):
            base64_str = base64.b64encode(screenshot_result).decode('utf-8')
            state.screenshot_url = f"data:image/png;base64,{base64_str}"
        else:
            logging.warning(f"Node {node_number}: Unexpected screenshot result format: {type(screenshot_result)}")
            state.screenshot_url = None
        
        logging.info(f"Node {node_number}: Screenshot captured - {description}")
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
async def click_85_60(state: State, config: RunnableConfig) -> State:
    """Initial click at (85, 60)"""
    return await click_action(state, config, 85, 60, "Initial click", 1)

async def click_233_234(state: State, config: RunnableConfig) -> State:
    """Click at (233, 234)"""
    return await click_action(state, config, 233, 234, "Click at text field", 2)

async def type_default_loan(state: State, config: RunnableConfig) -> State:
    """Type DEFAULT_LOAN text"""
    # Reconstruct the typed text from key press events
    typed_text = "DEFAULT_LOAN"
    state.typed_text = typed_text
    return await input_action(state, config, typed_text, "Type DEFAULT_LOAN", 3)

async def press_enter_key(state: State, config: RunnableConfig) -> State:
    """Press Enter key"""
    return await enter_action(state, config, "Press Enter", 4)

# Main workflow nodes
async def click_184_254_first(state: State, config: RunnableConfig) -> State:
    """First click at (184, 254)"""
    return await click_action(state, config, 184, 254, "First click at 184,254", 5)

async def click_184_254_second(state: State, config: RunnableConfig) -> State:
    """Second click at (184, 254)"""
    return await click_action(state, config, 184, 254, "Second click at 184,254", 6)

async def click_340_36(state: State, config: RunnableConfig) -> State:
    """Click at (340, 36)"""
    return await click_action(state, config, 340, 36, "Click at 340,36", 7)

async def click_391_65(state: State, config: RunnableConfig) -> State:
    """Click at (391, 65)"""
    return await click_action(state, config, 391, 65, "Click at 391,65", 8)

async def click_507_266(state: State, config: RunnableConfig) -> State:
    """Click at (507, 266)"""
    return await click_action(state, config, 507, 266, "Click at 507,266", 9)

async def click_846_545(state: State, config: RunnableConfig) -> State:
    """Click at (846, 545)"""
    return await click_action(state, config, 846, 545, "Click at 846,545", 10)

async def click_859_669(state: State, config: RunnableConfig) -> State:
    """Click at (859, 669)"""
    return await click_action(state, config, 859, 669, "Click at 859,669", 11)

async def click_134_65(state: State, config: RunnableConfig) -> State:
    """Click at (134, 65)"""
    return await click_action(state, config, 134, 65, "Click at 134,65", 12)

async def click_28_438(state: State, config: RunnableConfig) -> State:
    """Click at (28, 438)"""
    return await click_action(state, config, 28, 438, "Click at 28,438", 13)

async def click_77_540(state: State, config: RunnableConfig) -> State:
    """Click at (77, 540)"""
    return await click_action(state, config, 77, 540, "Click at 77,540", 14)

async def click_1350_541(state: State, config: RunnableConfig) -> State:
    """Click at (1350, 541)"""
    return await click_action(state, config, 1350, 541, "Click at 1350,541", 15)

async def click_878_313(state: State, config: RunnableConfig) -> State:
    """Click at (878, 313)"""
    return await click_action(state, config, 878, 313, "Click at 878,313", 16)

async def click_825_598(state: State, config: RunnableConfig) -> State:
    """Click at (825, 598)"""
    return await click_action(state, config, 825, 598, "Click at 825,598", 17)

async def click_765_447(state: State, config: RunnableConfig) -> State:
    """Click at (765, 447)"""
    return await click_action(state, config, 765, 447, "Click at 765,447", 18)

async def click_1339_97(state: State, config: RunnableConfig) -> State:
    """Click at (1339, 97)"""
    return await click_action(state, config, 1339, 97, "Click at 1339,97", 19)

async def click_743_443(state: State, config: RunnableConfig) -> State:
    """Click at (743, 443)"""
    return await click_action(state, config, 743, 443, "Click at 743,443", 20)

async def click_81_60(state: State, config: RunnableConfig) -> State:
    """Click at (81, 60)"""
    return await click_action(state, config, 81, 60, "Click at 81,60", 21)

async def click_327_99(state: State, config: RunnableConfig) -> State:
    """Click at (327, 99)"""
    return await click_action(state, config, 327, 99, "Click at 327,99", 22)

async def click_216_117(state: State, config: RunnableConfig) -> State:
    """Click at (216, 117)"""
    return await click_action(state, config, 216, 117, "Click at 216,117", 23)

async def click_23_65(state: State, config: RunnableConfig) -> State:
    """Click at (23, 65)"""
    return await click_action(state, config, 23, 65, "Click at 23,65", 24)

# Return phase nodes
async def click_1284_11(state: State, config: RunnableConfig) -> State:
    """Click at (1284, 11)"""
    return await click_action(state, config, 1284, 11, "Click at 1284,11", 25)

async def click_124_633_first(state: State, config: RunnableConfig) -> State:
    """First click at (124, 633)"""
    return await click_action(state, config, 124, 633, "First click at 124,633", 26)

async def click_124_633_second(state: State, config: RunnableConfig) -> State:
    """Second click at (124, 633)"""
    return await click_action(state, config, 124, 633, "Second click at 124,633", 27)

async def click_723_470(state: State, config: RunnableConfig) -> State:
    """Final click at (723, 470)"""
    return await click_action(state, config, 723, 470, "Final click at 723,470", 28)

# =============================================================================
# SUBGRAPH BUILDERS
# =============================================================================

def build_navigation_subgraph():
    """Build navigation subgraph for initial steps."""
    g = StateGraph(State)
    g.add_node("click_85_60", click_85_60)
    g.add_node("click_233_234", click_233_234)
    g.add_node("type_default_loan", type_default_loan)
    g.add_node("press_enter_key", press_enter_key)
    
    g.add_edge("__start__", "click_85_60")
    g.add_edge("click_85_60", "click_233_234")
    g.add_edge("click_233_234", "type_default_loan")
    g.add_edge("type_default_loan", "press_enter_key")
    g.add_edge("press_enter_key", "__end__")
    
    return g.compile(name="navigation_subgraph")

def build_main_workflow():
    """Build main workflow subgraph for core task steps."""
    g = StateGraph(State)
    g.add_node("click_184_254_first", click_184_254_first)
    g.add_node("click_184_254_second", click_184_254_second)
    g.add_node("click_340_36", click_340_36)
    g.add_node("click_391_65", click_391_65)
    g.add_node("click_507_266", click_507_266)
    g.add_node("click_846_545", click_846_545)
    g.add_node("click_859_669", click_859_669)
    g.add_node("click_134_65", click_134_65)
    g.add_node("click_28_438", click_28_438)
    g.add_node("click_77_540", click_77_540)
    g.add_node("click_1350_541", click_1350_541)
    g.add_node("click_878_313", click_878_313)
    g.add_node("click_825_598", click_825_598)
    g.add_node("click_765_447", click_765_447)
    g.add_node("click_1339_97", click_1339_97)
    g.add_node("click_743_443", click_743_443)
    g.add_node("click_81_60", click_81_60)
    g.add_node("click_327_99", click_327_99)
    g.add_node("click_216_117", click_216_117)
    g.add_node("click_23_65", click_23_65)
    
    g.add_edge("__start__", "click_184_254_first")
    g.add_edge("click_184_254_first", "click_184_254_second")
    g.add_edge("click_184_254_second", "click_340_36")
    g.add_edge("click_340_36", "click_391_65")
    g.add_edge("click_391_65", "click_507_266")
    g.add_edge("click_507_266", "click_846_545")
    g.add_edge("click_846_545", "click_859_669")
    g.add_edge("click_859_669", "click_134_65")
    g.add_edge("click_134_65", "click_28_438")
    g.add_edge("click_28_438", "click_77_540")
    g.add_edge("click_77_540", "click_1350_541")
    g.add_edge("click_1350_541", "click_878_313")
    g.add_edge("click_878_313", "click_825_598")
    g.add_edge("click_825_598", "click_765_447")
    g.add_edge("click_765_447", "click_1339_97")
    g.add_edge("click_1339_97", "click_743_443")
    g.add_edge("click_743_443", "click_81_60")
    g.add_edge("click_81_60", "click_327_99")
    g.add_edge("click_327_99", "click_216_117")
    g.add_edge("click_216_117", "click_23_65")
    g.add_edge("click_23_65", "__end__")
    
    return g.compile(name="main_workflow")

def build_return_subgraph():
    """Build return subgraph for cleanup steps."""
    g = StateGraph(State)
    g.add_node("click_1284_11", click_1284_11)
    g.add_node("click_124_633_first", click_124_633_first)
    g.add_node("click_124_633_second", click_124_633_second)
    g.add_node("click_723_470", click_723_470)
    
    g.add_edge("__start__", "click_1284_11")
    g.add_edge("click_1284_11", "click_124_633_first")
    g.add_edge("click_124_633_first", "click_124_633_second")
    g.add_edge("click_124_633_second", "click_723_470")
    g.add_edge("click_723_470", "__end__")
    
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
    """Build the main graph with subgraphs."""
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