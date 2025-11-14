#!/usr/bin/env python3
"""
Example usage of graph5.py - Modular LangGraph with controlled E2B + Claude steps

This example shows how to use the new modular workflow with better control and debugging.
"""

import os
import json
from dotenv import load_dotenv

def main():
    """Example usage of the modular workflow"""
    
    # Load environment variables
    load_dotenv()
    
    # Define your workflow specification
    # Change according to the input file you want to use
    json_path = os.path.join(os.path.dirname(__file__), 'tests', 'input', 'creditReportOutput.json')
    
    # Read json_path
    with open(json_path, 'r') as f:
        workflow_specification = json.load(f)
    
    # Define the target repository (where the code will be generated)
    target_repo_url = os.getenv("TARGET_GITHUB_REPO", "FintorAI/test-vibekit.git")
    
    # Get OS_URL from environment (for agent connection)
    os_url = os.getenv("OS_URL")  # Optional: OS URL for agent connection
    
    # Create the input for the workflow
    workflow_input = {
        "input_json": workflow_specification,
        "target_repo_url": target_repo_url,
        "download": True,
        "branch_name": "auto-generated-workflow",  # Optional: specify branch name (or None for auto-timestamp)
        "max_revision_attempts": 3,  # Optional: max code revision attempts (default 3)
        "os_url": os_url  # Optional: OS URL for agent connection (from .env)
    }
    
    print("🚀 Starting Modular LangGraph Workflow")
    print("=" * 50)
    print(f"Target Repository: {target_repo_url}")
    print(f"Workflow Specification: {len(json.dumps(workflow_specification))} chars")
    print(f"OS URL: {os_url if os_url else 'Not specified (will use simulation mode)'}")
    
    print("\n📋 Enhanced Modular Workflow Steps:")
    print("  1. 🔧 Create E2B sandbox")
    print("  2. 📥 Clone GitHub repository")
    print("  3. 🤖 Generate code with Claude")
    print("  4. 🔄 Enhanced Two-Phase Validation:")
    print("     Phase 1: Basic script execution (auto-installs packages)")
    print("     Phase 2: Setup langgraph.json + .env configuration") 
    print("     Phase 3: Write graph.py + LangGraph dev startup validation")
    print("  5. 🎯 Conditional flow based on validation result:")
    print("     ✅ Both phases pass → Local download → Git operations → Cleanup")
    print("     ❌ Any phase fails → Revise code with Claude → Test again (max 3 attempts)")
    print("     ❌ Still failing → Local download only → Cleanup")
    print("  6. 🔧 Git: checkout branch, proactive pull, commit deployment files, push")
    print("     📁 Commits: src/agent/graph.py, src/agent/__init__.py, .env, langgraph.json, requirements.txt")
    print("     🗂️ Proper Python package structure (ready for LangGraph Cloud)")
    print("  7. 🧹 Cleanup sandbox")
    
    print("\n💡 Benefits of Enhanced Approach:")
    print("  ✅ Each step is controllable and debuggable")
    print("  ✅ Can intervene if any step fails")
    print("  ✅ Clear error reporting per step")
    print("  ✅ Two-phase validation (basic + LangGraph dev)")
    print("  ✅ Intelligent code revision with differentiated prompts")
    print("  ✅ Auto-setup langgraph.json configuration")
    print("  ✅ Proactive git handling (prevents conflicts before they happen)")
    print("  ✅ Auto-configures git identity (no manual setup needed)")
    print("  ✅ Deployment-ready commits (includes .env + langgraph.json + requirements.txt for LangGraph Cloud)")
    print("\n🔑 Required Environment Variables:")
    print("  GITHUB_TOKEN - For repository access")
    print("  ANTHROPIC_API_KEY - For Claude API")
    print("  LANGSMITH_KEY - For LangSmith integration (LangGraph dev)")
    print("  PROMPT_PATH - Path to prompt template")
    print("  TEMPLATE_CODE_PATH - Path to template code for reference")
    print("  Optional: OPENAI_API_KEY - For OpenAI models if used")
    print("  Optional: GIT_EMAIL, GIT_NAME - Custom git identity")
    print("  Optional: OS_URL - OS URL for agent connection (e.g., http://localhost:8080)")
    print("  Optional: max_revision_attempts - Max code revision attempts")
    
    print("\n⚠️  This will consume E2B and Anthropic API credits!")
    
    # Show test without execution first
    print("\n🧪 Test input ready:")
    print(json.dumps(workflow_input, indent=2))
    
    # Uncomment to run the actual workflow
    print("\n" + "="*50)
    print("🔄 Executing modular workflow...")
    
    try:
        from graph5 import graph
        
        result = graph.invoke(workflow_input)
        
        print("\n✅ Workflow completed!")
        
        # Debug: Show the actual result structure
        print(f"📊 Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Safe access to result fields with defaults
        success = result.get('success', False)
        status = result.get('status', 'Unknown status')
        repo_cloned = result.get('repo_cloned', False)
        code_generated = result.get('code_generated', False)
        code_written = result.get('code_written', False)
        execution_successful = result.get('execution_successful', False)
        revision_attempts = result.get('revision_attempts', 0)
        last_error_name = result.get('last_error_name')
        last_error_value = result.get('last_error_value')
        last_error_type = result.get('last_error_type')  # NEW
        langgraph_config_setup = result.get('langgraph_config_setup', False)  # NEW
        langgraph_dev_tested = result.get('langgraph_dev_tested', False)  # NEW 
        langgraph_dev_successful = result.get('langgraph_dev_successful', False)  # NEW
        local_file_path = result.get('local_file_path')
        execution_result = result.get('result')
        git_branch = result.get('git_branch')
        commit_message = result.get('commit_message')
        git_pushed = result.get('git_pushed', False)
        error_log = result.get('error_log', [])
        
        print(f"Overall Success: {success}")
        print(f"Status: {status}")
        print(f"Repository Cloned: {repo_cloned}")
        print(f"Code Generated: {code_generated}")
        print(f"Code Written: {code_written}")
        
        # Show execution results
        if execution_result:
            print(f"🔄 Code Executed: ✅ Success")
            print(f"📤 Execution Output: {len(execution_result)} characters")
            # Show first few lines of execution output
            if execution_result.strip():
                output_lines = execution_result.split('\n')[:3]
                print(f"📋 Output Preview:")
                for i, line in enumerate(output_lines, 1):
                    if line.strip():
                        print(f"   {i}: {line.strip()}")
        else:
            print(f"🔄 Code Executed: ❌ Failed or no output")
        
        if local_file_path:
            print(f"📥 Downloaded Locally: {local_file_path}")
        else:
            print("📥 Local Download: Not requested or failed")
        
        # Show enhanced validation results
        if execution_successful:
            print(f"🔄 Enhanced Validation: ✅ Success")
            if langgraph_dev_tested:
                if langgraph_dev_successful:
                    print(f"   ✅ Basic execution + LangGraph dev both passed")
                else:
                    print(f"   ⚠️ Basic execution passed, LangGraph dev failed")
            else:
                print(f"   ⚠️ Only basic execution tested")
            if revision_attempts > 0:
                print(f"   💡 Required {revision_attempts} revision(s) to succeed")
        else:
            print(f"🔄 Enhanced Validation: ❌ Failed")
            if langgraph_config_setup:
                print(f"   ✅ LangGraph config setup successful")
            if langgraph_dev_tested:
                status = "✅ Passed" if langgraph_dev_successful else "❌ Failed"
                print(f"   🚀 LangGraph dev validation: {status}")
            if revision_attempts > 0:
                error_type_desc = "LangGraph dev" if last_error_type == "langgraph_dev" else "Basic execution"
                print(f"   🔄 Revision attempts: {revision_attempts} ({error_type_desc} errors)")
                if last_error_name and last_error_value:
                    print(f"   ❌ Final error ({last_error_type}): {last_error_name} - {last_error_value[:100]}...")
        
        # Show git operation results
        if git_branch:
            print(f"🌿 Git Branch: {git_branch}")
        if commit_message:
            print(f"💬 Commit Message: {commit_message}")
        if git_pushed:
            print("🚀 Git Push: ✅ Successfully pushed to remote")
        elif execution_successful:
            print("🚀 Git Push: ⚠️ Not pushed (check GitHub token)")
        elif not execution_successful:
            print("🚀 Git Operations: ⏭️ Skipped (execution failed)")
        
        # Check for errors
        if error_log and len(error_log) > 0:
            print(f"\n⚠️ Errors encountered ({len(error_log)}):")
            for i, error in enumerate(error_log, 1):
                print(f"   {i}. {error}")
        else:
            print(f"\n✅ No errors reported!")
        
        # Final result summary
        if success:
            print("\n🎉 Success! Code has been generated and written to graph.py")
            if execution_successful and git_pushed:
                print("   ✅ Full workflow completed with git operations!")
            elif execution_successful:
                print("   ✅ Code executed successfully but git push failed/skipped")
            elif revision_attempts > 0:
                print(f"   ⚠️ Code required {revision_attempts} revision(s) but still failed")
            else:
                print("   ❌ Code failed on first execution attempt")
        else:
            print(f"\n❌ Workflow failed. Check the errors above for debugging.")
            print("   Benefit: You can see exactly which step failed!")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure to run: pip install -r requirements-graph4.txt")
    except Exception as e:
        print(f"❌ Execution error: {e}")
    
    print("\n📚 Available commands:")
    print("  python test_graph5.py     - Run all tests")
    print("  python example_graph5_usage.py  - This example")

if __name__ == "__main__":
    main()
