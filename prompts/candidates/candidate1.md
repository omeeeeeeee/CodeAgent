You are a senior LangGraph engineer. Generate a Python file `graph.py` that, when executed, produces exactly the Target JSON. If Reference Code is present, use it only as guidance — do not copy. Output code only.

Target JSON:

{{INPUT_JSON}}

Reference Code (optional):

{{REFERENCE_CODE}}

Requirements:
- Define a minimal state and node functions to assemble the JSON.
- Build a simple graph (linear unless branching is required by the JSON).
- Ensure the compiled graph returns the Target JSON with exact values and types.
- Output only Python source for `graph.py`, no explanations.

