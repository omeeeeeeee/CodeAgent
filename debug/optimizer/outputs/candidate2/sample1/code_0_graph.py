from __future__ import annotations
import json
from typing import Union, Dict, Any, TypedDict
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

class State(TypedDict):
    user_input: Union[str, Dict[str, Any], None]
    current_node: int
    status: str
    borrower_name: str
    screenshot_url: Union[str, None]

def extract_borrower_name(state: State, config: RunnableConfig) -> State:
    if state.get("user_input"):
        borrower = None
        if isinstance(state["user_input"], dict):
            borrower = state["user_input"].get("borrower")
        elif isinstance(state["user_input"], str):
            try:
                user_data = json.loads(state["user_input"])
                if isinstance(user_data, dict):
                    borrower = user_data.get("borrower")
            except json.JSONDecodeError:
                pass
        if borrower:
            state["borrower_name"] = borrower
    state["current_node"] = 0
    state["status"] = "Initialized"
    return state

def click_pipeline(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 1
    state["status"] = "Success"
    return state

def wait_1s(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 2
    state["status"] = "Success"
    return state

def click_borrower_input(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 3
    state["status"] = "Success"
    return state

def input_name(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 4
    state["status"] = "Success"
    return state

def enter(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 5
    state["status"] = "Success"
    return state

def wait_3s(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 6
    state["status"] = "Success"
    return state

def double_click_borrower(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 7
    state["status"] = "Success"
    return state

def wait_3s_2(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 8
    state["status"] = "Success"
    return state

def click_services(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 9
    state["status"] = "Success"
    return state

def click_credit_report(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 10
    state["status"] = "Success"
    return state

def wait_5s_2(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 11
    state["status"] = "Success"
    return state

def click_credit_legacy(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 12
    state["status"] = "Success"
    return state

def click_submit(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 13
    state["status"] = "Success"
    return state

def wait_5s_3(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 14
    state["status"] = "Success"
    return state

def click_finish(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 15
    state["status"] = "Success"
    return state

def click_okay(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 16
    state["status"] = "Success"
    return state

def wait_30s(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 17
    state["status"] = "Success"
    return state

def screenshot(state: State, config: RunnableConfig) -> State:
    state["screenshot_url"] = "data:image/png;base64,screenshot_data_here"
    state["current_node"] = 18
    state["status"] = "Success"
    return state

def click_yes(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 19
    state["status"] = "Success"
    return state

def click_loan(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 20
    state["status"] = "Success"
    return state

def click_form_tab(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 21
    state["status"] = "Success"
    return state

def click_1003_form(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 22
    state["status"] = "Success"
    return state

def click_down(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 23
    state["status"] = "Success"
    return state

def click_import_liability(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 24
    state["status"] = "Success"
    return state

def wait_5s_4(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 25
    state["status"] = "Success"
    return state

def click_import(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 26
    state["status"] = "Success"
    return state

def click_ok(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 27
    state["status"] = "Success"
    return state

def wait_5s_5(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 28
    state["status"] = "Success"
    return state

def click_close(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 29
    state["status"] = "Success"
    return state

def click_no(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 30
    state["status"] = "Success"
    return state

def click_pipeline_return(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 31
    state["status"] = "Success"
    return state

def click_dropdown(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 32
    state["status"] = "Success"
    return state

def choose_all(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 33
    state["status"] = "Success"
    return state

def wait_5s_6(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 34
    state["status"] = "Success"
    return state

def click_home(state: State, config: RunnableConfig) -> State:
    state["current_node"] = 35
    state["status"] = "Success"
    return state

def produce_target_json(state: State, config: RunnableConfig) -> State:
    target_json = {
        "metadata": {
            "name": "lgCreditReportUnited",
            "description": "Credit Report Processing Workflow - H-Test-002",
            "source_template": "LG-blank",
            "target_agent": "LG-creditReport-united",
            "workflow_type": "linear"
        },
        "configuration": {
            "graph_name": "lgCreditReportUnited",
            "os_url": "https://fintor-ec2-united.ngrok.app",
            "default_borrower_name": "Graves, Sonnyy",
            "note": "All action functions already exist in template, OS_URL can be overridden"
        },
        "state_modifications": {
            "additional_fields": {
                "borrower_name": {
                    "type": "str",
                    "default": "Graves, Sonnyy",
                    "description": "Default borrower name"
                },
                "screenshot_url": {
                    "type": "Union[str, None]",
                    "default": None,
                    "description": "URL or data URI of captured screenshot"
                }
            },
            "note": "user_input, current_node, status already exist in template"
        },
        "additional_functions": {
            "extract_borrower_name": {
                "description": "Extract borrower name from user_input (string JSON or dict format)",
                "parameters": [
                    "state",
                    "config"
                ],
                "return_type": "State",
                "logic": "Parse user_input as JSON or dict, extract 'borrower' field, update state.borrower_name",
                "sets_fields": [
                    "borrower_name",
                    "current_node",
                    "status"
                ],
                "implementation_note": "Handle both dict and JSON string input formats"
            }
        },
        "subgraphs": {
            "navigation_subgraph": {
                "name": "navigation_subgraph",
                "type": "linear",
                "description": "Initial navigation and borrower selection",
                "nodes": [
                    {
                        "function_name": "extract_borrower_name",
                        "type": "special",
                        "description": "Extract borrower name from user_input",
                        "order": 1
                    },
                    {
                        "function_name": "click_pipeline",
                        "type": "click",
                        "description": "Coordinates for Pipeline",
                        "parameters": {
                            "x": 85,
                            "y": 60
                        },
                        "order": 2
                    },
                    {
                        "function_name": "wait_1s",
                        "type": "wait",
                        "description": "Sleep",
                        "parameters": {
                            "duration": 1
                        },
                        "order": 3
                    },
                    {
                        "function_name": "click_borrower_input",
                        "type": "click",
                        "description": "Coordinates for Borrower Name Input Box",
                        "parameters": {
                            "x": 333,
                            "y": 234
                        },
                        "order": 4
                    },
                    {
                        "function_name": "input_name",
                        "type": "input",
                        "description": "NAME",
                        "parameters": {
                            "text": "state.borrower_name"
                        },
                        "order": 5
                    },
                    {
                        "function_name": "enter",
                        "type": "enter",
                        "description": "ENTER",
                        "order": 6
                    },
                    {
                        "function_name": "wait_3s",
                        "type": "wait",
                        "description": "Sleep",
                        "parameters": {
                            "duration": 3
                        },
                        "order": 7
                    },
                    {
                        "function_name": "double_click_borrower",
                        "type": "double_click",
                        "description": "Coordinates for borrower name from the list",
                        "parameters": {
                            "x": 184,
                            "y": 254
                        },
                        "order": 8
                    },
                    {
                        "function_name": "wait_3s_2",
                        "type": "wait",
                        "description": "Sleep",
                        "parameters": {
                            "duration": 3
                        },
                        "order": 9
                    },
                    {
                        "function_name": "click_services",
                        "type": "click",
                        "description": "Coordinates for Services button",
                        "parameters": {
                            "x": 340,
                            "y": 36
                        },
                        "order": 10
                    }
                ]
            },
            "main_workflow": {
                "name": "main_workflow",
                "type": "linear",
                "description": "Credit report processing and form completion",
                "nodes": [
                    {
                        "function_name": "click_credit_report",
                        "type": "click",
                        "description": "Coordinates for Credit Report",
                        "parameters": {
                            "x": 391,
                            "y": 60
                        },
                        "order": 1
                    },
                    {
                        "function_name": "wait_5s_2",
                        "type": "wait",
                        "description": "Sleep",
                        "parameters": {
                            "duration": 5
                        },
                        "order": 2
                    },
                    {
                        "function_name": "click_credit_legacy",
                        "type": "click",
                        "description": "Coordinates for Advantage Credit Inc Legacy Credit",
                        "parameters": {
                            "x": 507,
                            "y": 266
                        },
                        "order": 3
                    },
                    {
                        "function_name": "click_submit",
                        "type": "click",
                        "description": "Coordinates for Submit Button",
                        "parameters": {
                            "x": 846,
                            "y": 545
                        },
                        "order": 4
                    },
                    {
                        "function_name": "wait_5s_3",
                        "type": "wait",
                        "description": "Sleep",
                        "parameters": {
                            "duration": 5
                        },
                        "order": 5
                    },
                    {
                        "function_name": "click_finish",
                        "type": "click",
                        "description": "Coordinates Finish Button",
                        "parameters": {
                            "x": 859,
                            "y": 669
                        },
                        "order": 6
                    },
                    {
                        "function_name": "click_okay",
                        "type": "click",
                        "description": "Click okay",
                        "parameters": {
                            "x": 1449,
                            "y": 849
                        },
                        "disabled": True,
                        "implementation": "return state",
                        "order": 7
                    },
                    {
                        "function_name": "wait_30s",
                        "type": "wait",
                        "description": "Wait 30 seconds",
                        "parameters": {
                            "duration": 30
                        },
                        "order": 8
                    },
                    {
                        "function_name": "screenshot",
                        "type": "screenshot",
                        "description": "Take a screenshot and store URL in state",
                        "order": 9
                    },
                    {
                        "function_name": "click_yes",
                        "type": "click",
                        "description": "Click yes",
                        "parameters": {
                            "x": 1273,
                            "y": 855
                        },
                        "disabled": True,
                        "implementation": "return state",
                        "order": 10
                    },
                    {
                        "function_name": "click_loan",
                        "type": "click",
                        "description": "Click loan",
                        "parameters": {
                            "x": 134,
                            "y": 65
                        },
                        "order": 11
                    },
                    {
                        "function_name": "click_form_tab",
                        "type": "click",
                        "description": "Click form tab",
                        "parameters": {
                            "x": 28,
                            "y": 438
                        },
                        "order": 12
                    },
                    {
                        "function_name": "click_1003_form",
                        "type": "click",
                        "description": "Click 1003 form",
                        "parameters": {
                            "x": 77,
                            "y": 540
                        },
                        "order": 13
                    },
                    {
                        "function_name": "click_down",
                        "type": "click",
                        "description": "Click down",
                        "parameters": {
                            "x": 1350,
                            "y": 541
                        },
                        "order": 14
                    },
                    {
                        "function_name": "click_import_liability",
                        "type": "click",
                        "description": "Click import liability",
                        "parameters": {
                            "x": 878,
                            "y": 313
                        },
                        "order": 15
                    },
                    {
                        "function_name": "wait_5s_4",
                        "type": "wait",
                        "description": "Wait 5 seconds",
                        "parameters": {
                            "duration": 5
                        },
                        "order": 16
                    },
                    {
                        "function_name": "click_import",
                        "type": "click",
                        "description": "Click import",
                        "parameters": {
                            "x": 825,
                            "y": 598
                        },
                        "order": 17
                    },
                    {
                        "function_name": "click_ok",
                        "type": "click",
                        "description": "Click ok",
                        "parameters": {
                            "x": 765,
                            "y": 447
                        },
                        "order": 18
                    },
                    {
                        "function_name": "wait_5s_5",
                        "type": "wait",
                        "description": "Wait 5 seconds",
                        "parameters": {
                            "duration": 5
                        },
                        "order": 19
                    },
                    {
                        "function_name": "click_close",
                        "type": "click",
                        "description": "Click close",
                        "parameters": {
                            "x": 1339,
                            "y": 97
                        },
                        "order": 20
                    }
                ]
            },
            "return_subgraph": {
                "name": "return_subgraph",
                "type": "linear",
                "description": "Return to home and cleanup",
                "nodes": [
                    {
                        "function_name": "click_no",
                        "type": "click",
                        "description": "Click no",
                        "parameters": {
                            "x": 743,
                            "y": 443
                        },
                        "order": 1
                    },
                    {
                        "function_name": "click_pipeline",
                        "type": "click",
                        "description": "Click pipeline",
                        "parameters": {
                            "x": 81,
                            "y": 60
                        },
                        "order": 2
                    },
                    {
                        "function_name": "click_dropdown",
                        "type": "click",
                        "description": "Click dropdown",
                        "parameters": {
                            "x": 327,
                            "y": 99
                        },
                        "order": 3
                    },
                    {
                        "function_name": "choose_all",
                        "type": "click",
                        "description": "Choose all",
                        "parameters": {
                            "x": 216,
                            "y": 117
                        },
                        "order": 4
                    },
                    {
                        "function_name": "wait_5s_6",
                        "type": "wait",
                        "description": "Wait 5 seconds",
                        "parameters": {
                            "duration": 5
                        },
                        "order": 5
                    },
                    {
                        "function_name": "click_home",
                        "type": "click",
                        "description": "Click home",
                        "parameters": {
                            "x": 23,
                            "y": 65
                        },
                        "order": 6
                    }
                ]
            }
        },
        "main_graph_flow": {
            "type": "linear",
            "subgraph_order": [
                "navigation_subgraph",
                "main_workflow",
                "return_subgraph"
            ],
            "note": "Each subgraph flows linearly to the next"
        },
        "generation_instructions": {
            "template_base": "LG-blank/src/agent/graph.py",
            "modifications_needed": [
                "Add extract_borrower_name function",
                "Update State model with borrower_name field",
                "Update OS_URL if different from template",
                "Create all node functions based on subgraph definitions",
                "Replace simple graph with subgraph-based linear flow",
                "Update graph name to 'lgCreditReportUnited'"
            ],
            "action_types_available": [
                "click - uses click_action function",
                "wait - uses wait_action function",
                "input - uses input_action function",
                "enter - uses enter_action function",
                "double_click - uses double_click_action function",
                "screenshot - uses screenshot_action function",
                "special - custom function implementation"
            ],
            "linear_flow_implementation": "For linear type, each node connects to the next in sequence within subgraph, and subgraphs connect in the order specified in main_graph_flow"
        }
    }
    state["target_json"] = target_json
    state["status"] = "Completed"
    return state

navigation_subgraph = (
    StateGraph(State)
    .add_node("extract_borrower_name", extract_borrower_name)
    .add_node("click_pipeline", click_pipeline)
    .add_node("wait_1s", wait_1s)
    .add_node("click_borrower_input", click_borrower_input)
    .add_node("input_name", input_name)
    .add_node("enter", enter)
    .add_node("wait_3s", wait_3s)
    .add_node("double_click_borrower", double_click_borrower)
    .add_node("wait_3s_2", wait_3s_2)
    .add_node("click_services", click_services)
    .add_edge("__start__", "extract_borrower_name")
    .add_edge("extract_borrower_name", "click_pipeline")
    .add_edge("click_pipeline", "wait_1s")
    .add_edge("wait_1s", "click_borrower_input")
    .add_edge("click_borrower_input", "input_name")
    .add_edge("input_name", "enter")
    .add_edge("enter", "wait_3s")
    .add_edge("wait_3s", "double_click_borrower")
    .add_edge("double_click_borrower", "wait_3s_2")
    .add_edge("wait_3s_2", "click_services")
    .add_edge("click_services", "__end__")
    .compile()
)

main_workflow = (
    StateGraph(State)
    .add_node("click_credit_report", click_credit_report)
    .add_node("wait_5s_2", wait_5s_2)
    .add_node("click_credit_legacy", click_credit_legacy)
    .add_node("click_submit", click_submit)
    .add_node("wait_5s_3", wait_5s_3)
    .add_node("click_finish", click_finish)
    .add_node("click_okay", click_okay)
    .add_node("wait_30s", wait_30s)
    .add_node("screenshot", screenshot)
    .add_node("click_yes", click_yes)
    .add_node("click_loan", click_loan)
    .add_node("click_form_tab", click_form_tab)
    .add_node("click_1003_form", click_1003_form)
    .add_node("click_down", click_down)
    .add_node("click_import_liability", click_import_liability)
    .add_node("wait_5s_4", wait_5s_4)
    .add_node("click_import", click_import)
    .add_node("click_ok", click_ok)
    .add_node("wait_5s_5", wait_5s_5)
    .add_node("click_close", click_close)
    .add_edge("__start__", "click_credit_report")
    .add_edge("click_credit_report", "wait_5s_2")
    .add_edge("wait_5s_2", "click_credit_legacy")
    .add_edge("click_credit_legacy", "click_submit")
    .add_edge("click_submit", "wait_5s_3")
    .add_edge("wait_5s_3", "click_finish")
    .add_edge("click_finish", "click_okay")
    .add_edge("click_okay", "wait_30s")
    .add_edge("wait_30s", "screenshot")
    .add_edge("screenshot", "click_yes")
    .add_edge("click_yes", "click_loan")
    .add_edge("click_loan", "click_form_tab")
    .add_edge("click_form_tab", "click_1003_form")
    .add_edge("click_1003_form", "click_down")
    .add_edge("click_down", "click_import_liability")
    .add_edge("click_import_liability", "wait_5s_4")
    .add_edge("wait_5s_4", "click_import")
    .add_edge("click_import", "click_ok")
    .add_edge("click_ok", "wait_5s_5")
    .add_edge("wait_5s_5", "click_close")
    .add_edge("click_close", "__end__")
    .compile()
)

return_subgraph = (
    StateGraph(State)
    .add_node("click_no", click_no)
    .add_node("click_pipeline_return", click_pipeline_return)
    .add_node("click_dropdown", click_dropdown)
    .add_node("choose_all", choose_all)
    .add_node("wait_5s_6", wait_5s_6)
    .add_node("click_home", click_home)
    .add_edge("__start__", "click_no")
    .add_edge("click_no", "click_pipeline_return")
    .add_edge("click_pipeline_return", "click_dropdown")
    .add_edge("click_dropdown", "choose_all")
    .add_edge("choose_all", "wait_5s_6")
    .add_edge("wait_5s_6", "click_home")
    .add_edge("click_home", "__end__")
    .compile()
)

graph = (
    StateGraph(State)
    .add_node("navigation_subgraph", navigation_subgraph)
    .add_node("main_workflow", main_workflow)
    .add_node("return_subgraph", return_subgraph)
    .add_node("produce_target_json", produce_target_json)
    .add_edge("__start__", "navigation_subgraph")
    .add_edge("navigation_subgraph", "main_workflow")
    .add_edge("main_workflow", "return_subgraph")
    .add_edge("return_subgraph", "produce_target_json")
    .add_edge("produce_target_json", "__end__")
    .compile(name="lgCreditReportUnited")
)