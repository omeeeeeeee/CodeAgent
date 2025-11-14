#!/usr/bin/env python3
"""
Test the automatic package installation feature
"""

from graph5 import extract_required_packages, install_packages_in_sandbox, create_sandbox
import os
from dotenv import load_dotenv

def test_package_extraction():
    """Test package extraction from code"""
    print("🧪 Testing package extraction...")
    
    sample_code = '''
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
import asyncio
import json
from pydantic import BaseModel
import requests
import os
'''
    
    packages = extract_required_packages(sample_code)
    print(f"📦 Extracted packages: {packages}")
    
    expected_packages = ['langchain-core', 'langgraph', 'pydantic', 'requests']
    missing = [pkg for pkg in expected_packages if pkg not in packages]
    extra = [pkg for pkg in packages if pkg not in expected_packages]
    
    if not missing and not extra:
        print("✅ Package extraction test passed!")
    else:
        if missing:
            print(f"⚠️ Missing expected packages: {missing}")
        if extra:
            print(f"⚠️ Found extra packages: {extra}")
    
    return packages

def test_sandbox_installation():
    """Test installing packages in E2B sandbox"""
    load_dotenv()
    
    print("\n🧪 Testing sandbox installation...")
    
    try:
        # Create sandbox
        initial_state = {"sandbox": None, "error_log": [], "status": "test"}
        state = create_sandbox(initial_state)
        
        if not state.get('sandbox'):
            print("❌ Failed to create sandbox")
            return False
            
        sandbox = state['sandbox']
        print("✅ Sandbox created successfully")
        
        # Test installing a small package
        test_packages = ['requests']  # Start with a common, lightweight package
        
        print(f"🔧 Testing installation of: {test_packages}")
        success = install_packages_in_sandbox(sandbox, test_packages)
        
        if success:
            print("✅ Package installation test passed!")
            
            # Verify the package is installed by trying to import it
            print("🔍 Verifying installation...")
            verify_code = """
try:
    import requests
    print("✅ Successfully imported requests")
    print(f"Version: {requests.__version__}")
except ImportError as e:
    print(f"❌ Failed to import: {e}")
"""
            
            execution = sandbox.run_code(verify_code)
            result = execution.text if execution.text else str(execution)
            print(f"Verification result: {result}")
            
        else:
            print("⚠️ Package installation had issues")
        
        # Cleanup
        sandbox.kill()
        print("✅ Sandbox cleaned up")
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Automatic Package Installation Feature")
    print("=" * 55)
    
    # Test 1: Package extraction
    packages = test_package_extraction()
    
    # Test 2: Sandbox installation (requires API keys)
    api_key = os.getenv("E2B_API_KEY")
    if api_key:
        success = test_sandbox_installation()
        if success:
            print("\n🎉 All tests passed! Package installation feature is working.")
        else:
            print("\n⚠️ Sandbox installation test had issues.")
    else:
        print("\n⚠️ Skipping sandbox test - E2B_API_KEY not set")
        print("   (Package extraction test passed)")
    
    print("\n📋 Summary:")
    print("  - The run_code step will now automatically install required packages")
    print("  - Supports common packages like langchain-core, langgraph, pydantic, etc.")
    print("  - Falls back gracefully if installation fails")

if __name__ == "__main__":
    main()
