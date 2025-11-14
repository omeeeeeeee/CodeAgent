"""LangGraph workflow based on JSON instructions.

Creates a graph following the H-Test-002 workflow with multiple action types.
"""

from __future__ import annotations

import json
from typing import Union, Dict, Any
from pydantic import BaseModel
import asyncio
import logging

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from cuteagent import WindowsAgent

class State(BaseModel):
    """Input state for the agent."""
    user_input: Union[str, Dict[str, Any], None] = None
    current_node: int = 0
    status: str = "Ongoing"
    borrower_name: str = "Graves, Sonnyy"  # Default borrower name
    screenshot_url: Union[str, None] = None

# Hardcoded OS URL
OS_URL = "https://fintor-ec2-united.ngrok.app"

async def extract_borrower_name(state: State, config: RunnableConfig) -> State:
    """Extract borrower name from user_input (string JSON or dict format)."""
    try:
        if state.user_input:
            borrower = None
            
            # Handle if user_input is already a dict
            if isinstance(state.user_input, dict):
                if "borrower" in state.user_input:
                    borrower = state.user_input["borrower"]
                    logging.info(f"Extracted borrower name from dict input: '{borrower}'")
                else:
                    logging.warning(f"No 'borrower' field found in dict input: {state.user_input}")
            
            # Handle if user_input is a string (JSON)
            elif isinstance(state.user_input, str):
                try:
                    user_data = json.loads(state.user_input)
                    if isinstance(user_data, dict) and "borrower" in user_data:
                        borrower = user_data["borrower"]
                        logging.info(f"Extracted borrower name from JSON string: '{borrower}'")
                    else:
                        logging.warning(f"No 'borrower' field found in JSON: {user_data}")
                except json.JSONDecodeError:
                    logging.warning(f"Could not parse user_input as JSON: {state.user_input}")
            
            # Update borrower_name if found
            if borrower:
                state.borrower_name = borrower
        else:
            logging.info("No user_input provided, using default borrower name")
        
        logging.info(f"Using borrower name: '{state.borrower_name}'")
        state.current_node = 0
        state.status = "Initialized"
        
    except Exception as e:
        logging.error(f"Error extracting borrower name: {e}")
        # Keep default borrower name on error
        state.status = "Warning"
    
    return state

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
        # For INPUT action, use the correct format from the example
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
        # For ENTER action, we'll use the act method with ENTER action
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

# H-Test-002 Workflow Nodes (based on the JSON instructions)

async def node_01_click_pipeline(state: State, config: RunnableConfig) -> State:
    """Order 1: CLICK - Coordinates for Pipeline"""
    return await click_action(85, 60, "Coordinates for Pipeline", 1, state)

async def node_02_wait_10s(state: State, config: RunnableConfig) -> State:
    """Order 2: WAIT - Sleep"""
    return await wait_action(1, "Sleep", 2, state)

async def node_03_click_borrower_input(state: State, config: RunnableConfig) -> State:
    """Order 3: CLICK - Coordinates for Borrower Name Input Box"""
    return await click_action(333, 234, "Coordinates for Borrower Name Input Box", 3, state)

async def node_04_input_name(state: State, config: RunnableConfig) -> State:
    """Order 4: INPUT - NAME"""
    return await input_action(state.borrower_name, "NAME", 4, state)

async def node_05_enter(state: State, config: RunnableConfig) -> State:
    """Order 5: ENTER - ENTER"""
    return await enter_action("ENTER", 5, state)

async def node_06_wait_10s_2(state: State, config: RunnableConfig) -> State:
    """Order 6: WAIT - Sleep"""
    return await wait_action(3, "Sleep", 6, state)

async def node_07_double_click_borrower(state: State, config: RunnableConfig) -> State:
    """Order 7: DOUBLE-CLICK - Coordinates for borrower name from the list"""
    return await double_click_action(184, 254, "Coordinates for borrower name from the list", 7, state)

async def node_08_wait_10s_3(state: State, config: RunnableConfig) -> State:
    """Order 8: WAIT - Sleep"""
    return await wait_action(3, "Sleep", 8, state)

async def node_09_click_services(state: State, config: RunnableConfig) -> State:
    """Order 9: CLICK - Coordinates for Services button"""
    return await click_action(340, 36, "Coordinates for Services button", 9, state)

async def node_10_click_credit_report(state: State, config: RunnableConfig) -> State:
    """Order 10: CLICK - Coordinates for Credit Report"""
    return await click_action(391, 60, "Coordinates for Credit Report", 10, state)

async def node_11_wait_20s(state: State, config: RunnableConfig) -> State:
    """Order 11: WAIT - Sleep"""
    return await wait_action(5, "Sleep", 11, state)

async def node_12_click_credit_legacy(state: State, config: RunnableConfig) -> State:
    """Order 13: CLICK - Coordinates for Advantage Credit Inc Legacy Credit"""
    return await click_action(507, 266, "Coordinates for Advantage Credit Inc Legacy Credit", 12, state)

async def node_13_click_submit(state: State, config: RunnableConfig) -> State:
    """Order 14: CLICK - Coordinates for Submit Button"""
    return await click_action(846, 545, "Coordinates for Submit Button", 13, state)

async def node_14_wait_30s(state: State, config: RunnableConfig) -> State:
    """Order 15: WAIT - Sleep"""
    return await wait_action(5, "Sleep", 14, state)

async def node_15_click_finish(state: State, config: RunnableConfig) -> State:
    """Order 16: CLICK - Coordinates Finish Button"""
    return await click_action(859, 669, "Coordinates Finish Button", 15, state)

# New nodes for extended workflow

async def node_16_click_okay(state: State, config: RunnableConfig) -> State:
    """Click okay button"""
    # return await click_action(1449, 849, "Click okay", 16, state)
    return state


async def node_17_wait_30s(state: State, config: RunnableConfig) -> State:
    """Wait 30 seconds"""
    return await wait_action(30, "Wait 10 seconds", 17, state)

async def node_18_screenshot(state: State, config: RunnableConfig) -> State:
    """Take a screenshot and store URL in state"""
    logging.info("Taking screenshot after wait")
    try:
        agent = WindowsAgent(os_url=OS_URL)
        screenshot_result = await asyncio.to_thread(agent.screenshot)
        
        if isinstance(screenshot_result, dict) and "url" in screenshot_result:
            state.screenshot_url = screenshot_result["url"]
            logging.info(f"Screenshot captured: {state.screenshot_url}")
        elif isinstance(screenshot_result, str):
            state.screenshot_url = screenshot_result
            logging.info(f"Screenshot captured: {state.screenshot_url}")
        elif isinstance(screenshot_result, bytes):
            import base64
            base64_str = base64.b64encode(screenshot_result).decode('utf-8')
            state.screenshot_url = f"data:image/png;base64,{base64_str}"
            logging.info("Screenshot captured as data URI")
        else:
            logging.warning(f"Unexpected screenshot result format: {type(screenshot_result)}")
            state.screenshot_url = None
    except Exception as e:
        logging.exception(f"Failed to take screenshot: {e}")
        state.screenshot_url = None
    
    state.current_node = 18
    state.status = "Success"
    return state

async def node_18_click_yes(state: State, config: RunnableConfig) -> State:
    """Click yes button"""
    # return await click_action(1273, 855, "Click yes", 18, state)
    return state

async def node_19_click_loan(state: State, config: RunnableConfig) -> State:
    # print we are going to loan
    return await click_action(134, 65, "Click loan", 19, state)

async def node_20_click_form_tab(state: State, config: RunnableConfig) -> State:
    """Click form tab"""
    return await click_action(28, 438, "Click form tab", 20, state)

async def node_21_click_1003_form(state: State, config: RunnableConfig) -> State:
    """Click 1003 form"""
    return await click_action(77, 540, "Click 1003 form", 21, state)

async def node_22_click_down(state: State, config: RunnableConfig) -> State:
    """Click down"""
    return await click_action(1350, 541, "Click down", 22, state)

async def node_23_click_import_liability(state: State, config: RunnableConfig) -> State:
    """Click import liability"""
    return await click_action(878, 313, "Click import liability", 23, state)

async def node_24_wait_5s(state: State, config: RunnableConfig) -> State:
    """Wait 5 seconds"""
    return await wait_action(5, "Wait 5 seconds", 24, state)

async def node_25_click_import(state: State, config: RunnableConfig) -> State:
    """Click import"""
    return await click_action(825, 598, "Click import", 25, state)

async def node_26_click_ok(state: State, config: RunnableConfig) -> State:
    """Click ok"""
    return await click_action(765, 447, "Click ok", 26, state)

async def node_27_wait_5s_2(state: State, config: RunnableConfig) -> State:
    """Wait 5 seconds"""
    return await wait_action(5, "Wait 5 seconds", 27, state)

async def node_28_click_close(state: State, config: RunnableConfig) -> State:
    """Click close"""
    return await click_action(1339, 97, "Click close", 28, state)

# Return subgraph nodes

async def return_01_click_no(state: State, config: RunnableConfig) -> State:
    """Return: Click no"""
    return await click_action(743, 443, "Click no", 101, state)

async def return_02_click_pipeline(state: State, config: RunnableConfig) -> State:
    """Return: Click pipeline"""
    return await click_action(81, 60, "Click pipeline", 102, state)

async def return_03_click_dropdown(state: State, config: RunnableConfig) -> State:
    """Return: Click dropdown"""
    return await click_action(327, 99, "Click dropdown", 103, state)

async def return_04_choose_all(state: State, config: RunnableConfig) -> State:
    """Return: Choose all"""
    return await click_action(216, 117, "Choose all", 104, state)

async def return_05_wait_5s(state: State, config: RunnableConfig) -> State:
    """Return: Wait 5 seconds"""
    return await wait_action(5, "Wait 5 seconds", 105, state)

async def return_06_click_home(state: State, config: RunnableConfig) -> State:
    """Return: Click home"""
    return await click_action(23, 65, "Click home", 106, state)

# Create Navigation subgraph (first 10 nodes)
navigation_graph = (
    StateGraph(State)
    .add_node("extract_borrower_name", extract_borrower_name)
    .add_node("node_01_click_pipeline", node_01_click_pipeline)
    .add_node("node_02_wait_10s", node_02_wait_10s)
    .add_node("node_03_click_borrower_input", node_03_click_borrower_input)
    .add_node("node_04_input_name", node_04_input_name)
    .add_node("node_05_enter", node_05_enter)
    .add_node("node_06_wait_10s_2", node_06_wait_10s_2)
    .add_node("node_07_double_click_borrower", node_07_double_click_borrower)
    .add_node("node_08_wait_10s_3", node_08_wait_10s_3)
    .add_node("node_09_click_services", node_09_click_services)
    .add_edge("__start__", "extract_borrower_name")
    .add_edge("extract_borrower_name", "node_01_click_pipeline")
    .add_edge("node_01_click_pipeline", "node_02_wait_10s")
    .add_edge("node_02_wait_10s", "node_03_click_borrower_input")
    .add_edge("node_03_click_borrower_input", "node_04_input_name")
    .add_edge("node_04_input_name", "node_05_enter")
    .add_edge("node_05_enter", "node_06_wait_10s_2")
    .add_edge("node_06_wait_10s_2", "node_07_double_click_borrower")
    .add_edge("node_07_double_click_borrower", "node_08_wait_10s_3")
    .add_edge("node_08_wait_10s_3", "node_09_click_services")
    .add_edge("node_09_click_services", "__end__")
    .compile(name="navigation_subgraph")
)

# Create Return subgraph
return_graph = (
    StateGraph(State)
    .add_node("return_01_click_no", return_01_click_no)
    .add_node("return_02_click_pipeline", return_02_click_pipeline)
    .add_node("return_03_click_dropdown", return_03_click_dropdown)
    .add_node("return_04_choose_all", return_04_choose_all)
    .add_node("return_05_wait_5s", return_05_wait_5s)
    .add_node("return_06_click_home", return_06_click_home)
    .add_edge("__start__", "return_01_click_no")
    .add_edge("return_01_click_no", "return_02_click_pipeline")
    .add_edge("return_02_click_pipeline", "return_03_click_dropdown")
    .add_edge("return_03_click_dropdown", "return_04_choose_all")
    .add_edge("return_04_choose_all", "return_05_wait_5s")
    .add_edge("return_05_wait_5s", "return_06_click_home")
    .add_edge("return_06_click_home", "__end__")
    .compile(name="return_subgraph")
)

# Define the main graph with subgraphs
graph = (
    StateGraph(State)
    .add_node("navigation", navigation_graph)
    .add_node("node_10_click_credit_report", node_10_click_credit_report)
    .add_node("node_11_wait_20s", node_11_wait_20s)
    .add_node("node_12_click_credit_legacy", node_12_click_credit_legacy)
    .add_node("node_13_click_submit", node_13_click_submit)
    .add_node("node_14_wait_30s", node_14_wait_30s)
    .add_node("node_15_click_finish", node_15_click_finish)
    .add_node("node_16_click_okay", node_16_click_okay)
    .add_node("node_17_wait_30s", node_17_wait_30s)
    .add_node("node_18_screenshot", node_18_screenshot)
    .add_node("node_18_click_yes", node_18_click_yes)
    .add_node("node_19_click_loan", node_19_click_loan)
    .add_node("node_20_click_form_tab", node_20_click_form_tab)
    .add_node("node_21_click_1003_form", node_21_click_1003_form)
    .add_node("node_22_click_down", node_22_click_down)
    .add_node("node_23_click_import_liability", node_23_click_import_liability)
    .add_node("node_24_wait_5s", node_24_wait_5s)
    .add_node("node_25_click_import", node_25_click_import)
    .add_node("node_26_click_ok", node_26_click_ok)
    .add_node("node_27_wait_5s_2", node_27_wait_5s_2)
    .add_node("node_28_click_close", node_28_click_close)
    .add_node("return_workflow", return_graph)
    .add_edge("__start__", "navigation")
    .add_edge("navigation", "node_10_click_credit_report")
    .add_edge("node_10_click_credit_report", "node_11_wait_20s")
    .add_edge("node_11_wait_20s", "node_12_click_credit_legacy")
    .add_edge("node_12_click_credit_legacy", "node_13_click_submit")
    .add_edge("node_13_click_submit", "node_14_wait_30s")
    .add_edge("node_14_wait_30s", "node_15_click_finish")
    .add_edge("node_15_click_finish", "node_17_wait_30s")
    .add_edge("node_17_wait_30s", "node_18_screenshot")
    .add_edge("node_18_screenshot", "node_18_click_yes")
    .add_edge("node_18_click_yes", "node_19_click_loan")
    .add_edge("node_19_click_loan", "node_20_click_form_tab")
    .add_edge("node_20_click_form_tab", "node_21_click_1003_form")
    .add_edge("node_21_click_1003_form", "node_22_click_down")
    .add_edge("node_22_click_down", "node_23_click_import_liability")
    .add_edge("node_23_click_import_liability", "node_24_wait_5s")
    .add_edge("node_24_wait_5s", "node_25_click_import")
    .add_edge("node_25_click_import", "node_26_click_ok")
    .add_edge("node_26_click_ok", "node_27_wait_5s_2")
    .add_edge("node_27_wait_5s_2", "node_28_click_close")
    .add_edge("node_28_click_close", "return_workflow")
    .add_edge("return_workflow", "__end__")
    .compile(
        name="lgCreditReportUnited",
    )
)