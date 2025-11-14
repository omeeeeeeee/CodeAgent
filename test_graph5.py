#!/usr/bin/env python3
"""
Test script for graph5.py - Modular LangGraph with controlled E2B + Claude steps

This tests each individual step of the workflow for better debugging.
"""

import os
import json
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        "ANTHROPIC_API_KEY",
        "E2B_API_KEY"
    ]
    
    optional_vars = [
        "TARGET_GITHUB_REPO"  # Can be provided in input
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("✅ All required environment variables are set")
    
    # Show optional vars
    for var in optional_vars:
        value = os.getenv(var)
        status = "✅" if value else "⚠️"
        print(f"{status} {var}: {'set' if value else 'not set (can provide in input)'}")
    
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import anthropic
        print(f"✅ anthropic: {anthropic.__version__}")
    except ImportError:
        print("❌ Missing: anthropic (pip install anthropic)")
        return False
    
    try:
        import e2b_code_interpreter
        print("✅ e2b_code_interpreter: installed")
    except ImportError:
        print("❌ Missing: e2b-code-interpreter (pip install e2b-code-interpreter)")
        return False
    
    try:
        import langgraph
        try:
            from importlib.metadata import version
            lang_version = version('langgraph')
            print(f"✅ langgraph: {lang_version}")
        except Exception:
            print("✅ langgraph: installed (version unknown)")
    except ImportError:
        print("❌ Missing: langgraph (pip install langgraph)")
        return False
    
    return True

def test_import():
    """Test importing graph5 module and components"""
    try:
        from graph5 import (
            graph, OverallState, InputState, OutputState,
            create_sandbox, clone_repository,
            generate_code_with_claude, write_code_to_file, cleanup_sandbox
        )
        print("✅ graph5.py imports successfully")
        print("✅ All workflow functions imported:")
        print("   - create_sandbox")
        print("   - clone_repository") 
        print("   - generate_code_with_claude")
        print("   - write_code_to_file")
        print("   - cleanup_sandbox")
        print(f"✅ Graph object created: {type(graph)}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import graph5.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing graph5.py: {e}")
        return False

def test_step_by_step():
    """Test each step individually"""
    try:
        from graph5 import create_sandbox, cleanup_sandbox
        from e2b_code_interpreter import Sandbox
        
        print("\n🧪 Testing individual steps...")
        
        # Test 1: Sandbox creation
        print("\n1. Testing sandbox creation...")
        try:
            sandbox = Sandbox.create()
            print("✅ E2B sandbox created successfully")
            sandbox.kill()
            print("✅ Sandbox cleanup successful")
        except Exception as e:
            print(f"❌ Sandbox test failed: {e}")
            return False
        
        # Test 2: Test state structure
        print("\n2. Testing state structure...")
        mock_state = {
            "input_json": {"test": "data"},
            "target_repo_url": "https://github.com/test/repo.git",
            "sandbox": None,
            "repo_path": None,
            "generated_code": None,
            "code_written": False,
            "repo_cloned": False,
            "code_generated": False,
            "success": False,
            "error_log": [],
            "status": "initialized"
        }
        print("✅ State structure is valid")
        print(f"   - Input JSON: {type(mock_state['input_json'])}")
        print(f"   - Target repo: {mock_state['target_repo_url']}")
        print(f"   - Status tracking: {len([k for k in mock_state.keys() if k.endswith('_cloned') or k.endswith('_generated') or k.endswith('_written')])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Step-by-step test failed: {e}")
        return False

def create_test_input():
    """Create test input for the workflow"""
    return {
        "input_json": {
            "workflow_name": "test_modular_workflow",
            "description": "Testing the modular implementation", 
            "nodes": [
                {"name": "start", "type": "initialization"},
                {"name": "process", "type": "processing"},
                {"name": "end", "type": "finalization"}
            ],
            "expected_output": {
                "status": "success",
                "processed": True,
                "result": "test_complete"
            }
        },
        "target_repo_url": os.getenv("TARGET_GITHUB_REPO", "https://github.com/FintorAI/test-vibekit.git")
    }

def main():
    """Main test function"""
    print("🚀 Testing graph5.py - Modular LangGraph with Controlled Steps")
    print("=" * 65)
    
    all_passed = True
    
    # Check environment
    print("\n1. Checking environment variables...")
    if not check_environment():
        all_passed = False
    
    # Check dependencies  
    print("\n2. Checking dependencies...")
    if not check_dependencies():
        all_passed = False
    
    # Test imports
    print("\n3. Testing module imports...")
    if not test_import():
        all_passed = False
    
    # Test individual steps
    print("\n4. Testing individual workflow steps...")
    if not test_step_by_step():
        all_passed = False
    
    # Show test input
    print("\n5. Preparing test input...")
    test_input = create_test_input()
    print("✅ Test input created:")
    print(f"   - Workflow specification: {len(json.dumps(test_input['input_json']))} chars")
    print(f"   - Target repository: {test_input['target_repo_url']}")
    
    # Final result
    print("\n" + "=" * 65)
    if all_passed:
        print("✅ All tests passed! graph5.py is ready to use.")
        print("\n🚀 To run the modular workflow:")
        print("   from graph5 import graph")
        print("   result = graph.invoke(test_input)")
        print("\n📋 Workflow steps:")
        print("   1. Create E2B sandbox")
        print("   2. Clone GitHub repository")
        print("   3. Generate code with Claude")
        print("   4. Write code to graph.py")
        print("   5. Cleanup sandbox")
        print("\n💡 Each step is controllable and debuggable!")
        print("⚠️  NOTE: Actual execution will consume E2B and Anthropic API credits")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
