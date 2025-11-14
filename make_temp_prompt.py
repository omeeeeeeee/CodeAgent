import json
from datetime import datetime

def main():
    # Read the base prompt template
    with open("prompts/base_08-27-25.md", "r", encoding="utf-8") as f:
        template_text = f.read()
    
    # Read the workflow config JSON
    with open("tests/input/workflow_config.json", "r", encoding="utf-8") as f:
        workflow_config = json.load(f)
    
    # Replace the INPUT_JSON placeholder with the pretty-printed JSON
    rendered_prompt = template_text.replace(
        "{{INPUT_JSON}}", json.dumps(workflow_config, indent=2)
    )
    
    # Create the temp_prompt.json structure
    prompt_data = {
        "prompt": rendered_prompt,
        "timestamp": datetime.now().isoformat()
    }
    
    # Save to temp_prompt.json
    with open("temp_prompt.json", "w", encoding="utf-8") as f:
        json.dump(prompt_data, f, ensure_ascii=False, indent=2)
    
    print("Successfully created temp_prompt.json")
    print(f"Prompt length: {len(rendered_prompt)} characters")

if __name__ == "__main__":
    main()
