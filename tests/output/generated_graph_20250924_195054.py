"""LangGraph workflow for Credit Report Processing - H-Test-002"""

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

GRAPH_NAME = "lgCreditReportUnited"
OS_URL = "https://fintor-ec2-united.ngrok.app"

# =============================================================================
# STATE DEFINITION
# =============================================================================

class State(BaseModel):
    """State for the credit report processing workflow."""
    user_input: Union[str, Dict[str, Any], None] = None
    current_node: int = 0
    status: str = ""
    has_error: bool = False
    borrower_name: str = "Graves, Sonnyy"
    screenshot_url: Union[str, None] = None

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
        from cuteagent import WindowsAgent
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
# ADDITIONAL FUNCTIONS
# =============================================================================

async def extract_borrower_name(state: State, config: RunnableConfig) -> State:
    """Extract borrower name from user_input (string JSON or dict format)."""
    try:
        data = state.user_input
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                logging.warning("user_input not JSON; keeping defaults")
                data = {}
        
        if isinstance(data, dict) and data.get("borrower"):
            state.borrower_name = str(data["borrower"]).strip()
            logging.info(f"Extracted borrower name: {state.borrower_name}")
        
        state.status = "Initialized"
    except Exception as e:
        logging.exception("extract_borrower_name failed")
        state.status = "Warning"
    
    state.current_node = 1
    return state

# =============================================================================
# NAVIGATION SUBGRAPH NODES
# =============================================================================

async def nav_extract_borrower_name(state: State, config: RunnableConfig) -> State:
    return await extract_borrower_name(state, config)

async def nav_click_pipeline(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 85, 60, "Coordinates for Pipeline", 2)

async def nav_wait_1s(state: State, config: RunnableConfig) -> State:
    return await wait_action(state, config, 1, "Sleep", 3)

async def nav_click_borrower_input(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 333, 234, "Coordinates for Borrower Name Input Box", 4)

async def nav_input_name(state: State, config: RunnableConfig) -> State:
    return await input_action(state, config, "state.borrower_name", "NAME", 5)

async def nav_enter(state: State, config: RunnableConfig) -> State:
    return await enter_action(state, config, "ENTER", 6)

async def nav_wait_3s(state: State, config: RunnableConfig) -> State:
    return await wait_action(state, config, 3, "Sleep", 7)

async def nav_double_click_borrower(state: State, config: RunnableConfig) -> State:
    return await double_click_action(state, config, 184, 254, "Coordinates for borrower name from the list", 8)

async def nav_wait_3s_2(state: State, config: RunnableConfig) -> State:
    return await wait_action(state, config, 3, "Sleep", 9)

async def nav_click_services(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 340, 36, "Coordinates for Services button", 10)

# =============================================================================
# MAIN WORKFLOW NODES
# =============================================================================

async def main_click_credit_report(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 391, 60, "Coordinates for Credit Report", 1)

async def main_wait_5s_2(state: State, config: RunnableConfig) -> State:
    return await wait_action(state, config, 5, "Sleep", 2)

async def main_click_credit_legacy(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 507, 266, "Coordinates for Advantage Credit Inc Legacy Credit", 3)

async def main_click_submit(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 846, 545, "Coordinates for Submit Button", 4)

async def main_wait_5s_3(state: State, config: RunnableConfig) -> State:
    return await wait_action(state, config, 5, "Sleep", 5)

async def main_click_finish(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 859, 669, "Coordinates Finish Button", 6)

async def main_click_okay(state: State, config: RunnableConfig) -> State:
    """Disabled node - no-op implementation."""
    logging.info("Node 7: Skipped (disabled) - Click okay")
    state.current_node = 7
    state.status = "Success"
    return state

async def main_wait_30s(state: State, config: RunnableConfig) -> State:
    return await wait_action(state, config, 30, "Wait 30 seconds", 8)

async def main_screenshot(state: State, config: RunnableConfig) -> State:
    return await screenshot_action(state, config, "Take a screenshot and store URL in state", 9)

async def main_click_yes(state: State, config: RunnableConfig) -> State:
    """Disabled node - no-op implementation."""
    logging.info("Node 10: Skipped (disabled) - Click yes")
    state.current_node = 10
    state.status = "Success"
    return state

async def main_click_loan(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 134, 65, "Click loan", 11)

async def main_click_form_tab(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 28, 438, "Click form tab", 12)

async def main_click_1003_form(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 77, 540, "Click 1003 form", 13)

async def main_click_down(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 1350, 541, "Click down", 14)

async def main_click_import_liability(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 878, 313, "Click import liability", 15)

async def main_wait_5s_4(state: State, config: RunnableConfig) -> State:
    return await wait_action(state, config, 5, "Wait 5 seconds", 16)

async def main_click_import(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 825, 598, "Click import", 17)

async def main_click_ok(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 765, 447, "Click ok", 18)

async def main_wait_5s_5(state: State, config: RunnableConfig) -> State:
    return await wait_action(state, config, 5, "Wait 5 seconds", 19)

async def main_click_close(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 1339, 97, "Click close", 20)

# =============================================================================
# RETURN SUBGRAPH NODES
# =============================================================================

async def return_click_no(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 743, 443, "Click no", 1)

async def return_click_pipeline(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 81, 60, "Click pipeline", 2)

async def return_click_dropdown(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 327, 99, "Click dropdown", 3)

async def return_choose_all(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 216, 117, "Choose all", 4)

async def return_wait_5s_6(state: State, config: RunnableConfig) -> State:
    return await wait_action(state, config, 5, "Wait 5 seconds", 5)

async def return_click_home(state: State, config: RunnableConfig) -> State:
    return await click_action(state, config, 23, 65, "Click home", 6)

# =============================================================================
# SUBGRAPH BUILDERS
# =============================================================================

def build_navigation_subgraph():
    """Build the navigation subgraph."""
    g = StateGraph(State)
    g.add_node("extract_borrower_name", nav_extract_borrower_name)
    g.add_node("click_pipeline", nav_click_pipeline)
    g.add_node("wait_1s", nav_wait_1s)
    g.add_node("click_borrower_input", nav_click_borrower_input)
    g.add_node("input_name", nav_input_name)
    g.add_node("enter", nav_enter)
    g.add_node("wait_3s", nav_wait_3s)
    g.add_node("double_click_borrower", nav_double_click_borrower)
    g.add_node("wait_3s_2", nav_wait_3s_2)
    g.add_node("click_services", nav_click_services)
    
    # Linear flow
    g.add_edge("__start__", "extract_borrower_name")
    g.add_edge("extract_borrower_name", "click_pipeline")
    g.add_edge("click_pipeline", "wait_1s")
    g.add_edge("wait_1s", "click_borrower_input")
    g.add_edge("click_borrower_input", "input_name")
    g.add_edge("input_name", "enter")
    g.add_edge("enter", "wait_3s")
    g.add_edge("wait_3s", "double_click_borrower")
    g.add_edge("double_click_borrower", "wait_3s_2")
    g.add_edge("wait_3s_2", "click_services")
    g.add_edge("click_services", "__end__")
    
    return g.compile(name="navigation_subgraph")

def build_main_workflow():
    """Build the main workflow subgraph."""
    g = StateGraph(State)
    g.add_node("click_credit_report", main_click_credit_report)
    g.add_node("wait_5s_2", main_wait_5s_2)
    g.add_node("click_credit_legacy", main_click_credit_legacy)
    g.add_node("click_submit", main_click_submit)
    g.add_node("wait_5s_3", main_wait_5s_3)
    g.add_node("click_finish", main_click_finish)
    g.add_node("click_okay", main_click_okay)
    g.add_node("wait_30s", main_wait_30s)
    g.add_node("screenshot", main_screenshot)
    g.add_node("click_yes", main_click_yes)
    g.add_node("click_loan", main_click_loan)
    g.add_node("click_form_tab", main_click_form_tab)
    g.add_node("click_1003_form", main_click_1003_form)
    g.add_node("click_down", main_click_down)
    g.add_node("click_import_liability", main_click_import_liability)
    g.add_node("wait_5s_4", main_wait_5s_4)
    g.add_node("click_import", main_click_import)
    g.add_node("click_ok", main_click_ok)
    g.add_node("wait_5s_5", main_wait_5s_5)
    g.add_node("click_close", main_click_close)
    
    # Linear flow
    g.add_edge("__start__", "click_credit_report")
    g.add_edge("click_credit_report", "wait_5s_2")
    g.add_edge("wait_5s_2", "click_credit_legacy")
    g.add_edge("click_credit_legacy", "click_submit")
    g.add_edge("click_submit", "wait_5s_3")
    g.add_edge("wait_5s_3", "click_finish")
    g.add_edge("click_finish", "click_okay")
    g.add_edge("click_okay", "wait_30s")
    g.add_edge("wait_30s", "screenshot")
    g.add_edge("screenshot", "click_yes")
    g.add_edge("click_yes", "click_loan")
    g.add_edge("click_loan", "click_form_tab")
    g.add_edge("click_form_tab", "click_1003_form")
    g.add_edge("click_1003_form", "click_down")
    g.add_edge("click_down", "click_import_liability")
    g.add_edge("click_import_liability", "wait_5s_4")
    g.add_edge("wait_5s_4", "click_import")
    g.add_edge("click_import", "click_ok")
    g.add_edge("click_ok", "wait_5s_5")
    g.add_edge("wait_5s_5", "click_close")
    g.add_edge("click_close", "__end__")
    
    return g.compile(name="main_workflow")

def build_return_subgraph():
    """Build the return subgraph."""
    g = StateGraph(State)
    g.add_node("click_no", return_click_no)
    g.add_node("click_pipeline", return_click_pipeline)
    g.add_node("click_dropdown", return_click_dropdown)
    g.add_node("choose_all", return_choose_all)
    g.add_node("wait_5s_6", return_wait_5s_6)
    g.add_node("click_home", return_click_home)
    
    # Linear flow
    g.add_edge("__start__", "click_no")
    g.add_edge("click_no", "click_pipeline")
    g.add_edge("click_pipeline", "click_dropdown")
    g.add_edge("click_dropdown", "choose_all")
    g.add_edge("choose_all", "wait_5s_6")
    g.add_edge("wait_5s_6", "click_home")
    g.add_edge("click_home", "__end__")
    
    return g.compile(name="return_subgraph")

# =============================================================================
# FINALIZER
# =============================================================================

async def finalize_state(state: State, config: RunnableConfig) -> State:
    """Final state processing."""
    state.status = "Error" if state.has_error else "Completed"
    logging.info(f"Workflow completed with status: {state.status}")
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
    
    # Linear flow through subgraphs
    g.add_edge("__start__", "navigation_subgraph")
    g.add_edge("navigation_subgraph", "main_workflow")
    g.add_edge("main_workflow", "return_subgraph")
    g.add_edge("return_subgraph", "finalize_state")
    g.add_edge("finalize_state", "__end__")
    
    return g.compile(name=GRAPH_NAME)

graph = build_main_graph()