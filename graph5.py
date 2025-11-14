# Modular Langgraph agent workflow with E2B + Claude (controlled steps):
# 1. Clone GitHub repository in E2B sandbox (controlled)
# 2. Extract JSON configuration (controlled)  
# 3. Generate LangGraph code with Claude (controlled)
# 4. Write code to file (controlled)
# 5. [Future] Test execution, commit, PR creation

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict

from langchain_anthropic import ChatAnthropic
from e2b_code_interpreter import Sandbox
from langgraph.graph import END, StateGraph, START
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class InputState(TypedDict):
    """Input to the workflow"""
    input_json: str | dict  # JSON specification for the agent
    target_repo_url: str    # GitHub repository URL to clone and modify
    download: Optional[bool]  # Optional: download generated code locally
    branch_name: Optional[str]  # Optional: branch name for git operations
    max_revision_attempts: Optional[int]  # Optional: max revision attempts (default 3)
    os_url: Optional[str]  # Optional: OS URL for agent connection

class OutputState(TypedDict):
    """Output from the workflow"""
    status: str
    success: bool
    repo_cloned: bool
    code_generated: bool
    error_log: List[str]
    code_written: bool
    local_file_path: Optional[str]  # Path to locally downloaded file
    execution: Any | None
    result: str | None
    revision_attempts: int  # Number of revision attempts made
    execution_successful: bool  # Whether code execution was successful
    last_error_name: Optional[str]  # Error name from last execution (for debugging)
    last_error_value: Optional[str]  # Error value from last execution (for debugging)
    last_error_type: Optional[str]  # NEW: "execution" or "langgraph_dev"
    last_error_details: Optional[str]  # NEW: Full error context
    langgraph_config_setup: bool  # NEW: Whether langgraph.json was setup
    langgraph_dev_tested: bool  # NEW: Whether langgraph dev was tested
    langgraph_dev_successful: bool  # NEW: Whether langgraph dev passed
    git_branch: Optional[str]  # Created branch name
    commit_message: Optional[str]  # Generated commit message  
    git_pushed: bool  # Whether changes were pushed

class OverallState(TypedDict):
    """Complete workflow state"""
    # Input
    input_json: dict
    target_repo_url: str
    download: Optional[bool]  # Option to download generated code locally
    branch_name: Optional[str]  # Branch name for git operations
    os_url: Optional[str]  # OS URL for agent connection
    
    # Sandbox management
    sandbox: Any | None
    repo_path: str | None
    
    # Code generation
    generated_code: str | None
    code_written: bool
    local_file_path: Optional[str]  # Path to locally downloaded file
    
    # Code execution
    execution: Any | None
    result: str | None
    execution_successful: bool  # Track if code execution was successful
    
    # Code revision (for failed executions)
    revision_attempts: int  # Number of revision attempts made
    last_error_name: Optional[str]  # Error name from last execution
    last_error_value: Optional[str]  # Error value from last execution
    last_error_type: Optional[str]  # NEW: "execution" or "langgraph_dev"
    last_error_details: Optional[str]  # NEW: Full error context
    max_revision_attempts: int  # Maximum revision attempts (default 3)
    
    # LangGraph validation (NEW)
    langgraph_config_setup: bool  # Whether langgraph.json was setup
    langgraph_dev_tested: bool  # Whether langgraph dev was tested
    langgraph_dev_successful: bool  # Whether langgraph dev passed
    
    # Git operations
    git_branch: Optional[str]  # Created branch name
    commit_message: Optional[str]  # Generated commit message
    git_pushed: bool  # Whether changes were pushed
    
    # Status tracking
    repo_cloned: bool
    code_generated: bool
    success: bool
    error_log: List[str]
    status: str

# Step 1: Create sandbox
def create_sandbox(state: OverallState) -> OverallState:
    """Create and initialize E2B sandbox"""
    try:
        print("🔧 Creating E2B sandbox...")
        sandbox = Sandbox.create()
        print("✅ E2B sandbox created successfully")
        
        return {
            **state,
            "sandbox": sandbox,
            "revision_attempts": 0,  # Initialize revision counter
            "max_revision_attempts": state.get("max_revision_attempts", 3),  # Default to 3 attempts
            "last_error_name": None,
            "last_error_value": None,
            "last_error_type": None,  # NEW: Initialize error type
            "last_error_details": None,  # NEW: Initialize error details
            "execution_successful": False,  # Initialize as False
            "langgraph_config_setup": False,  # NEW: Initialize langgraph config
            "langgraph_dev_tested": False,  # NEW: Initialize langgraph dev testing
            "langgraph_dev_successful": False,  # NEW: Initialize langgraph dev success
            "git_pushed": False,  # Initialize as False
            "git_branch": None,  # Initialize as None
            "commit_message": None,  # Initialize as None
            "status": "Sandbox created successfully"
        }
        
    except Exception as e:
        error_message = f"Failed to create sandbox: {str(e)}"
        print(f"❌ {error_message}")
        return {
            **state,
            "sandbox": None,
            "revision_attempts": 0,
            "max_revision_attempts": state.get("max_revision_attempts", 3),
            "last_error_name": None,
            "last_error_value": None,
            "last_error_type": None,  # NEW: Initialize error type
            "last_error_details": None,  # NEW: Initialize error details
            "execution_successful": False,
            "langgraph_config_setup": False,  # NEW: Initialize langgraph config
            "langgraph_dev_tested": False,  # NEW: Initialize langgraph dev testing
            "langgraph_dev_successful": False,  # NEW: Initialize langgraph dev success
            "git_pushed": False,
            "git_branch": None,
            "commit_message": None,
            "error_log": state.get("error_log", []) + [error_message],
            "status": error_message
        }

# Step 2: Clone repository
def clone_repository_with_token(state: OverallState) -> OverallState:
    """Clone the target repository in the E2B sandbox with the token"""
    try:
        sandbox = state.get("sandbox")
        if not sandbox:
            raise ValueError("No sandbox available")
        
        repo_url = state["target_repo_url"]  # e.g., "FintorAI/test-vibekit.git" 
        print(f"📥 Cloning repository: {repo_url}")
        
        # Extract repo name for directory
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        
        # Remove existing directory if it exists (ensure clean clone)
        print(f"🧹 Cleaning up any existing '{repo_name}' directory...")
        cleanup_result = sandbox.commands.run(f'rm -rf {repo_name}')
        if cleanup_result.exit_code == 0:
            print(f"✅ Cleaned up existing directory (or none existed)")
        else:
            print(f"⚠️ Cleanup warning: {cleanup_result.stderr}")
        
        # Clone with token authentication
        github_token = os.getenv("GITHUB_TOKEN")
        clone_url = f'https://{github_token}@github.com/{repo_url}'
        
        print(f"📥 Cloning fresh copy...")
        result = sandbox.commands.run(f'git clone {clone_url} {repo_name}')
        
        print(f"Git clone result:")
        print(f"  Exit code: {result.exit_code}")
        print(f"  Stdout: {result.stdout}")
        print(f"  Stderr: {result.stderr}")
        
        if result.exit_code == 0:
            print(f"✅ Repository cloned successfully to: {repo_name}")
            
            # Verify the directory exists
            verify_result = sandbox.commands.run(f'ls -la {repo_name}')
            if verify_result.exit_code == 0:
                print(f"📁 Repository contents:")
                print(verify_result.stdout)
            
            return {
                **state,
                "repo_path": repo_name,
                "repo_cloned": True,
                "status": f"Repository cloned successfully to {repo_name}"
            }
        else:
            error_msg = f"Git clone failed with exit code {result.exit_code}: {result.stderr}"
            raise ValueError(error_msg)
            
    except Exception as e:
        error_message = f"Failed to clone repository: {str(e)}"
        print(f"❌ {error_message}")
        return {
            **state,
            "repo_path": None,
            "repo_cloned": False,
            "error_log": state.get("error_log", []) + [error_message],
            "status": error_message
        }

# Step 3: Generate code with Claude
def generate_code_with_claude(state: OverallState) -> OverallState:
    """Generate LangGraph code using Claude"""
    try:
        print("🤖 Generating code with Claude...")
        
        # Initialize ChatAnthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        
        client = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            max_tokens=8000,
            temperature=0
        )
        
        # Prepare context
        input_json = state["input_json"]
        
        # Get prompt path 
        # Revised to get os path instead of local path from env 
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "base_09-04-25_v3.md") # os.getenv("PROMPT_PATH")

        # Read prompt
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        # Replace variable in prompt with input_json
        prompt = prompt.replace("{{INPUT_JSON}}", json.dumps(input_json, indent=2))
        
        # Get template code path
        # Revised to use os path instead of local path from env 
        TEMPLATE_CODE_PATH = os.path.join(os.path.dirname(__file__), "graph_template.py") # os.getenv("TEMPLATE_CODE_PATH")

        # Read template code
        with open(TEMPLATE_CODE_PATH, "r", encoding="utf-8") as f:
            template_code = f.read()

        # Replace variable in prompt with template code
        prompt = prompt.replace("{{TEMPLATE_CODE}}", template_code)
        
        # Replace OS_URL variable in prompt
        os_url = state.get("os_url", "None")
        prompt = prompt.replace("{{OS_URL}}", str(os_url))

        print(f"\n===========================\n Prompt: {prompt} \n===========================\n")

        # Generate code with Claude
        print("🔄 Calling Claude API...")
        messages = [
            ("human", prompt)
        ]
        response = client.invoke(messages)
        
        # Extract generated code
        generated_code = response.content
        
        if not generated_code:
            raise ValueError("Claude did not generate any code")
        
        # Try to extract Python code blocks if wrapped in markdown
        if "```python" in generated_code:
            start = generated_code.find("```python")
            end = generated_code.find("```", start + 8)
            if start != -1 and end != -1:
                generated_code = generated_code[start + 9:end].strip()
        elif "```" in generated_code:
            start = generated_code.find("```")
            end = generated_code.find("```", start + 3)
            if start != -1 and end != -1:
                generated_code = generated_code[start + 3:end].strip()
        
        print(f"✅ Claude generated {len(generated_code)} characters of code")
        print("Generated code preview (first 200 chars):")
        print(generated_code[:200] + "..." if len(generated_code) > 200 else generated_code)
        
        return {
            **state,
            "generated_code": generated_code,
            "code_generated": True,
            "status": f"Code generated successfully ({len(generated_code)} chars)"
        }
        
    except Exception as e:
        error_message = f"Failed to generate code with Claude: {str(e)}"
        print(f"❌ {error_message}")
        return {
            **state,
            "generated_code": None,
            "code_generated": False,
            "error_log": state.get("error_log", []) + [error_message],
            "status": error_message
        }

# Prep for Step 4: Run code
def extract_required_packages(code: str) -> List[str]:
    """Extract package names from import statements in the generated code"""
    import re
    
    packages = set()
    
    # Common package mappings (import name -> pip package name)
    package_mappings = {
        'langchain_core': 'langchain-core',
        'langchain_community': 'langchain-community', 
        'langchain_openai': 'langchain-openai',
        'langgraph': 'langgraph',
        'pydantic': 'pydantic',
        'typing_extensions': 'typing-extensions',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'requests': 'requests',
        'aiohttp': 'aiohttp',
        'httpx': 'httpx',
        'openai': 'openai',
        'anthropic': 'anthropic'
    }
    
    # Extract import statements
    lines = code.split('\n')
    for line in lines:
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue
            
        # Match "from package import ..." or "import package"
        import_match = re.match(r'^(?:from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)|import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*?))', line)
        
        if import_match:
            package_name = import_match.group(1) or import_match.group(2)
            
            # Get the root package name
            root_package = package_name.split('.')[0]
            
            # Skip built-in modules
            builtin_modules = {
                '__future__', 'os', 'sys', 'json', 'time', 'datetime', 'asyncio', 'typing', 
                're', 'functools', 'collections', 'itertools', 'pathlib',
                'logging', 'uuid', 'hashlib', 'base64', 'urllib', 'http',
                'email', 'csv', 'xml', 'sqlite3', 'threading', 'multiprocessing',
                'copy', 'pickle', 'socket', 'struct', 'math', 'random', 'string',
                'io', 'contextlib', 'warnings', 'traceback', 'inspect', 'gc',
                'weakref', 'operator', 'abc', 'enum', 'dataclasses'
            }
            
            if root_package not in builtin_modules:
                # Map to pip package name if known
                pip_package = package_mappings.get(root_package, root_package)
                packages.add(pip_package)
    
    return sorted(list(packages))

# Prep for Step 4: Run code
def install_packages_in_sandbox(sandbox, packages: List[str]) -> bool:
    """Install required packages in the E2B sandbox"""
    if not packages:
        return True
    
    # Filter out any obviously problematic packages
    valid_packages = []
    for pkg in packages:
        # Skip packages that are clearly invalid
        if pkg and not pkg.startswith('_') and pkg.replace('-', '').replace('_', '').isalnum():
            valid_packages.append(pkg)
        else:
            print(f"⚠️ Skipping invalid package: {pkg}")
    
    if not valid_packages:
        print("📦 No valid packages to install")
        return True
    
    try:
        # Try batch installation first
        packages_str = ' '.join(valid_packages)
        install_cmd = f'pip install {packages_str}'
        
        print(f"🔧 Running: {install_cmd}")
        
        # Execute pip install
        result = sandbox.commands.run(install_cmd)
        
        print(f"📦 Batch installation result:")
        print(f"   Exit code: {result.exit_code}")
        
        if result.stdout:
            # Show last few lines of stdout (usually the success messages)
            stdout_lines = result.stdout.strip().split('\n')
            print(f"   Output (last 3 lines):")
            for line in stdout_lines[-3:]:
                if line.strip():
                    print(f"     {line.strip()}")
        
        if result.exit_code == 0:
            print("✅ Batch package installation completed successfully")
            return True
        else:
            print(f"⚠️ Batch installation failed (exit code: {result.exit_code})")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()[:200]}")
            
            # Try installing packages individually
            print("🔄 Attempting individual package installation...")
            success_count = 0
            
            for package in valid_packages:
                try:
                    individual_cmd = f'pip install {package}'
                    print(f"   🔧 Installing {package}...")
                    
                    individual_result = sandbox.commands.run(individual_cmd)
                    
                    if individual_result.exit_code == 0:
                        print(f"   ✅ {package} installed successfully")
                        success_count += 1
                    else:
                        print(f"   ⚠️ {package} failed to install")
                        
                except Exception as e:
                    print(f"   ❌ {package} installation error: {e}")
            
            print(f"📊 Individual installation summary: {success_count}/{len(valid_packages)} packages installed")
            return success_count > 0  # Return True if at least one package installed
            
    except Exception as e:
        print(f"❌ Package installation failed: {e}")
        return False

# Step 4: Enhanced run code with two-phase validation
def run_code(state: OverallState) -> OverallState:
    """Enhanced validation: Basic execution + LangGraph dev testing"""
    
    # Phase 1: Basic script execution (existing logic)
    basic_result = run_basic_execution(state)
    
    # If basic execution fails, return immediately
    if not basic_result.get("execution_successful", False):
        return basic_result
    
    # Phase 2: Setup LangGraph configuration
    print("\n🔧 Phase 2: Setting up LangGraph environment...")
    config_result = setup_langgraph_config(basic_result)
    
    # If config setup fails, still continue but mark as basic-only success
    if not config_result.get("langgraph_config_setup", False):
        print("⚠️ LangGraph config setup failed, but basic execution was successful")
        return {
            **config_result,
            "execution_successful": True,  # Keep basic success
            "status": "Basic execution successful, but LangGraph config setup failed"
        }
    
    # Phase 3: LangGraph dev validation
    print("\n🚀 Phase 3: Testing LangGraph dev...")
    langgraph_result = test_langgraph_dev(config_result)
    
    # Check final validation status
    basic_success = langgraph_result.get("execution_successful", False)
    langgraph_success = langgraph_result.get("langgraph_dev_successful", False)
    
    if basic_success and langgraph_success:
        print("✅ All validations passed!")
        return {
            **langgraph_result,
            "status": "Full validation successful (basic execution + LangGraph dev)"
        }
    elif basic_success:
        print("⚠️ Basic execution passed, but LangGraph dev failed")
        return {
            **langgraph_result,
            "execution_successful": False,  # Mark as failed overall for revision
            "status": "Basic execution successful, but LangGraph dev validation failed"
        }
    else:
        # This shouldn't happen since we returned early, but safety check
        return langgraph_result

def run_basic_execution(state: OverallState) -> OverallState:
    """Run basic script execution (Phase 1 of validation)"""
    try:
        sandbox = state.get("sandbox")
        if not sandbox:
            raise ValueError("No sandbox available")
        
        generated_code = state.get("generated_code")
        
        if not generated_code:
            raise ValueError("No generated code available")
        
        print("🔄 Phase 1: Testing basic code execution...")
        print(f"📝 Code length: {len(generated_code)} characters")
        
        # First, let's preview the first few lines
        code_lines = generated_code.split('\n')[:5]
        print("📄 Code preview (first 5 lines):")
        for i, line in enumerate(code_lines, 1):
            print(f"   {i}: {line}")
        
        # Extract and install required packages
        print("\n📦 Installing required packages...")
        required_packages = extract_required_packages(generated_code)
        if required_packages:
            print(f"📋 Found {len(required_packages)} packages to install: {', '.join(required_packages)}")
            install_success = install_packages_in_sandbox(sandbox, required_packages)
            if not install_success:
                print("⚠️ Some packages failed to install, but continuing with execution...")
        else:
            print("📋 No external packages detected")
        
        # Execute the generated code
        print("\n🚀 Executing generated code...")
        execution = sandbox.run_code(generated_code)
        
        # Handle different ways to get the output
        result_text = ""
        if hasattr(execution, 'text') and execution.text:
            result_text = execution.text
        elif hasattr(execution, 'logs') and hasattr(execution.logs, 'stdout'):
            result_text = execution.logs.stdout
        elif hasattr(execution, 'stdout'):
            result_text = execution.stdout
        else:
            result_text = str(execution)
        
        # Check if execution was successful and extract error details
        success = True
        error_info = ""
        error_name = None
        error_value = None
        
        if hasattr(execution, 'error') and execution.error:
            success = False
            error_info = str(execution.error)
            # Extract error name and value from ExecutionError
            if hasattr(execution.error, 'name'):
                error_name = execution.error.name
            if hasattr(execution.error, 'value'):
                error_value = execution.error.value
            elif "ExecutionError(name=" in error_info:
                # Parse error from string format: ExecutionError(name='ValueError', value='message', ...)
                import re
                name_match = re.search(r"name='([^']+)'", error_info)
                value_match = re.search(r"value='([^']+)'", error_info)
                if name_match:
                    error_name = name_match.group(1)
                if value_match:
                    error_value = value_match.group(1)
        elif hasattr(execution, 'logs') and hasattr(execution.logs, 'stderr') and execution.logs.stderr:
            error_info = execution.logs.stderr

            # Added to address "Failed to run code: 'list' object has no attribute 'lower'" error (Sept 4 2025 3:52 PM)
            # Convert to string if it's a list
            if isinstance(error_info, list):
                error_info = '\n'.join(str(item) for item in error_info)
            elif not isinstance(error_info, str):
                error_info = str(error_info)

            # Only mark as failed if stderr contains actual errors (not warnings)
            if "error" in error_info.lower() or "traceback" in error_info.lower():
                success = False
                # Try to extract error type from traceback
                if "Error:" in error_info:
                    error_lines = error_info.split('\n')
                    for line in error_lines:
                        if "Error:" in line:
                            error_name = line.split(':')[0].strip().split()[-1]
                            error_value = ':'.join(line.split(':')[1:]).strip()
                            break
        
        if success:
            print(f"✅ Basic execution successful!")
            print(f"📤 Output length: {len(result_text)} characters")
            if result_text:
                # Show first few lines of output
                output_lines = result_text.split('\n')[:3]
                print("📋 Output preview:")
                for i, line in enumerate(output_lines, 1):
                    if line.strip():  # Only show non-empty lines
                        print(f"   {i}: {line}")
            
            status_msg = f"Basic execution successful ({len(result_text)} chars output)"
        else:
            print(f"⚠️ Basic execution had issues:")
            print(f"   Error info: {error_info}")
            status_msg = f"Basic execution failed: {error_info}"
        
        return {
            **state,
            "execution": execution,
            "result": result_text,
            "execution_successful": success,
            "last_error_type": "execution" if not success else None,
            "last_error_name": error_name,
            "last_error_value": error_value,
            "last_error_details": error_info if not success else None,
            "status": status_msg
        }

    except Exception as e:
        error_message = f"Failed to run basic execution: {str(e)}"
        print(f"❌ {error_message}")
        
        # Provide debug information
        print("🔍 Debug info:")
        print(f"   - Sandbox available: {sandbox is not None}")
        print(f"   - Generated code available: {generated_code is not None}")
        if generated_code:
            print(f"   - Code length: {len(generated_code)}")
        
        return {
            **state,
            "execution": None,
            "result": None,
            "execution_successful": False,
            "last_error_type": "execution",
            "last_error_name": "ExecutionException",
            "last_error_value": str(e),
            "last_error_details": error_message,
            "error_log": state.get("error_log", []) + [error_message],
            "status": error_message
        }

# Step 4.1: Setup LangGraph configuration
def setup_langgraph_config(state: OverallState) -> OverallState:
    """Copy langgraph.json template and create .env file in sandbox"""
    try:
        sandbox = state.get("sandbox")
        repo_path = state.get("repo_path")
        
        if not sandbox or not repo_path:
            raise ValueError("Sandbox or repository path not available")
        
        print("🔧 Setting up LangGraph environment...")
        
        # Step 1: Setup langgraph.json (pointing to generated graph.py)
        print("📄 Setting up langgraph.json...")
        
        # Create langgraph.json config for the generated graph
        langgraph_config = {
            "dependencies": ["./"],
            "graphs": {
                "agent": "./src/agent/graph.py:graph"
            },
            "env": ".env",
            "image_distro": "wolfi"
        }
        
        config_content = json.dumps(langgraph_config, indent=2)
        remote_config = f"{repo_path}/langgraph.json"
        sandbox.files.write(remote_config, config_content)
        print("✅ langgraph.json configured (pointing to ./src/agent/graph.py:graph)")
        
        # Step 2: Setup .env file with required environment variables
        print("🔑 Setting up .env file...")
        env_vars = []
        
        # Get LANGSMITH_KEY from local environment
        langsmith_key = os.getenv("LANGSMITH_KEY")
        if langsmith_key:
            env_vars.append(f"LANGSMITH_KEY={langsmith_key}")
            print("✅ LANGSMITH_KEY added to .env")
        else:
            print("⚠️ LANGSMITH_KEY not found in local environment")
        
        # Optionally add other useful env vars for LangGraph dev
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            env_vars.append(f"ANTHROPIC_API_KEY={anthropic_key}")
            print("✅ ANTHROPIC_API_KEY added to .env")
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            env_vars.append(f"OPENAI_API_KEY={openai_key}")
            print("✅ OPENAI_API_KEY added to .env")
        
        # Write .env file to sandbox
        if env_vars:
            env_content = "\n".join(env_vars) + "\n"
            remote_env = f"{repo_path}/.env"
            sandbox.files.write(remote_env, env_content)
            print(f"✅ .env file created with {len(env_vars)} variables")
        else:
            print("⚠️ No environment variables to add to .env file")
        
        return {
            **state,
            "langgraph_config_setup": True,
            "status": f"LangGraph environment setup successful (config + {len(env_vars)} env vars)"
        }
        
    except Exception as e:
        error_message = f"Failed to setup LangGraph environment: {str(e)}"
        print(f"❌ {error_message}")
        return {
            **state,
            "langgraph_config_setup": False,
            "error_log": state.get("error_log", []) + [error_message],
            "status": error_message
        }

# Step 4.2: Find available port in sandbox
def find_available_port(sandbox, start_port: int = 8123) -> int:
    """Find an available port in the sandbox"""
    for port in range(start_port, start_port + 10):
        try:
            # Check if port is in use
            check_cmd = f"netstat -an | grep :{port}"
            result = sandbox.commands.run(check_cmd)
            if result.exit_code != 0:  # Port not found = available
                return port
        except:
            continue
    return start_port  # Fallback to original

# Step 4.3: Test LangGraph dev startup
def test_langgraph_dev(state: OverallState, timeout: int = 5) -> OverallState:
    """Test langgraph dev startup and basic functionality"""
    try:
        sandbox = state.get("sandbox")
        repo_path = state.get("repo_path")
        
        if not sandbox or not repo_path:
            raise ValueError("Sandbox or repository path not available")
        
        # Step 1: Ensure langgraph CLI with inmem support is installed
        print("📦 Ensuring LangGraph CLI with inmem support is installed...")
        install_result = sandbox.commands.run('pip install -U "langgraph-cli[inmem]"')
        
        if install_result.exit_code == 0:
            print("✅ LangGraph CLI with inmem support installed successfully")
        else:
            print(f"⚠️ LangGraph CLI installation warning: {install_result.stderr}")
            # Continue anyway - might already be installed
        
        # Step 2: Write generated code to src/agent/graph.py (required for langgraph dev)
        generated_code = state.get("generated_code")
        if not generated_code:
            raise ValueError("No generated code available for LangGraph dev testing")
        
        print("💾 Writing generated code to src/agent/graph.py for LangGraph dev testing...")
        
        # Create src/agent directory structure
        src_dir = f"{repo_path}/src"
        agent_dir = f"{repo_path}/src/agent"
        
        # Create directories (E2B handles this automatically when writing files)
        print("📁 Creating src/agent/ directory structure...")
        
        # Write __init__.py file (only in agent package)
        sandbox.files.write(f"{agent_dir}/__init__.py", "# agent package") 
        
        # Write the main graph.py file
        graph_file_path = f"{agent_dir}/graph.py"
        sandbox.files.write(graph_file_path, generated_code)
        print("✅ src/agent/graph.py written to sandbox with package structure")
        
        # Step 3: Find available port
        port = find_available_port(sandbox)
        
        print(f"🔧 Testing LangGraph dev startup on port {port}...")
        
        # Step 4: Start dev server with timeout (will run briefly then exit)
        dev_cmd = f"cd {repo_path} && timeout {timeout}s langgraph dev --host 0.0.0.0 --port {port} 2>&1 || true"
        
        result = sandbox.commands.run(dev_cmd)
        
        # Check output for startup success indicators or specific errors
        output = (result.stdout or "") + (result.stderr or "")
        output_lower = output.lower()
        
        print(f"📊 LangGraph dev output: ...{output}\n")
        
        # Success indicators (based on actual LangGraph dev output)
        success_indicators = [
            "server started in",  # "Server started in 2.97s"
            "🚀 api:",  # "🚀 API: http://0.0.0.0:8123"
            "registering graph with id",  # "Registering graph with id 'agent'" 
            "welcome to",  # LangGraph welcome banner
            "server running",
            "listening on",
            "application startup complete"
        ]
        
        # Error indicators
        error_indicators = [
            "compilation failed",
            "graph compilation failed", 
            "missing graph",
            "graph 'graph' not found",
            "invalid state",
            "state schema error",
            "traceback",
            "error:",
            "failed to start",
            "module not found"
        ]
        
        has_success = any(indicator in output_lower for indicator in success_indicators)
        has_error = any(indicator in output_lower for indicator in error_indicators)
        
        if has_success and not has_error:
            print("✅ LangGraph dev started successfully")
            return {
                **state,
                "langgraph_dev_tested": True,
                "langgraph_dev_successful": True,
                "code_written": True,  # Mark as written since we wrote to sandbox
                "status": "LangGraph dev validation successful"
            }
        else:
            # Parse specific error types
            if "compilation failed" in output_lower or "graph compilation failed" in output_lower:
                error_type = "Graph compilation failed"
            elif "missing graph" in output_lower or "graph 'graph' not found" in output_lower:
                error_type = "Graph export missing"
            elif "invalid state" in output_lower or "state schema error" in output_lower:
                error_type = "State schema error"
            elif "module not found" in output_lower:
                error_type = "Missing dependencies"
            else:
                error_type = "LangGraph dev startup failed"
                
            print(f"⚠️ LangGraph dev failed: {error_type}")
            
            return {
                **state,
                "langgraph_dev_tested": True,
                "langgraph_dev_successful": False,
                "code_written": True,  # File was written, just failed validation
                "last_error_type": "langgraph_dev",
                "last_error_name": error_type,
                "last_error_value": f"LangGraph dev validation failed",
                "last_error_details": output[-500:],  # Last 500 chars for debugging
                "status": f"LangGraph dev validation failed: {error_type}"
            }
            
    except Exception as e:
        error_message = f"LangGraph dev test failed: {str(e)}"
        print(f"❌ {error_message}")
        
        return {
            **state,
            "langgraph_dev_tested": True,
            "langgraph_dev_successful": False,
            "code_written": True,  # File was written before exception
            "last_error_type": "langgraph_dev",
            "last_error_name": "LangGraph dev test exception",
            "last_error_value": str(e),
            "last_error_details": error_message,
            "error_log": state.get("error_log", []) + [error_message],
            "status": error_message
        }

# Step 4.5: Revise code (when execution fails)
def revise_code_with_claude(state: OverallState) -> OverallState:
    """Revise code using Claude based on execution error"""
    try:
        print("🔄 Revising code with Claude based on execution error...")
        
        # Initialize ChatAnthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        
        client = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            max_tokens=8000,
            temperature=0
        )
        
        # Get current state
        generated_code = state.get("generated_code", "")
        error_name = state.get("last_error_name", "Unknown")
        error_value = state.get("last_error_value", "Unknown error")
        revision_attempts = state.get("revision_attempts", 0)
        
        print(f"📊 Revision attempt #{revision_attempts + 1}")
        print(f"❌ Error to fix: {error_name} - {error_value}")
        
        # Create differentiated revision prompt based on error type
        error_type = state.get("last_error_type", "execution")
        
        if error_type == "langgraph_dev":
            # LangGraph-specific prompt
            revision_prompt = f"""You are a LangGraph expert helping to fix a LangGraph workflow that failed during `langgraph dev` startup.

ORIGINAL CODE:
```python
{generated_code}
```

LANGGRAPH DEV ERROR:
Error Type: {error_name}
Error Message: {error_value}
Full Error Details: {state.get("last_error_details", "")[-500:]}

TASK:
Fix the above code to resolve the LangGraph development server error. Focus specifically on:
1. Graph compilation issues (StateGraph, nodes, edges)  
2. Graph export requirements (MUST have top-level 'graph = ...')
3. LangGraph configuration compatibility
4. State schema validation and proper Pydantic models
5. Proper subgraph compilation if applicable
6. Correct imports for langgraph components

COMMON LANGGRAPH DEV ISSUES:
- Missing "graph = build_graph()" at module level
- StateGraph compilation errors  
- Invalid state schema (ensure Pydantic BaseModel)
- Incorrect edge definitions
- Missing imports (StateGraph, END, START, etc.)

REQUIREMENTS:
- Return ONLY the corrected Python code
- MUST include "graph = ..." export at module level
- Ensure StateGraph is properly compiled
- Do not include explanations or markdown formatting
- Maintain the same general structure and functionality

CORRECTED CODE:"""
        else:
            # Basic execution error prompt (original)
            revision_prompt = f"""You are a Python expert helping to fix a LangGraph workflow that failed during basic execution.

ORIGINAL CODE:
```python
{generated_code}
```

EXECUTION ERROR:
Error Type: {error_name}
Error Message: {error_value}

TASK:
Fix the above code to resolve the execution error. Focus specifically on:
1. The {error_name} error that occurred
2. Making sure the LangGraph workflow is properly structured
3. Ensuring all required imports are present
4. Adding proper error handling if needed
5. Fixing syntax errors, missing variables, or import issues

REQUIREMENTS:
- Return ONLY the corrected Python code
- Do not include explanations or markdown formatting
- Maintain the same general structure and functionality
- Fix the specific error that caused the failure

CORRECTED CODE:"""

        print("🔄 Calling Claude API for code revision...")
        messages = [
            ("human", revision_prompt)
        ]
        response = client.invoke(messages)
        
        # Extract revised code
        revised_code = response.content
        
        if not revised_code:
            raise ValueError("Claude did not generate revised code")
        
        # Try to extract Python code blocks if wrapped in markdown
        if "```python" in revised_code:
            start = revised_code.find("```python")
            end = revised_code.find("```", start + 8)
            if start != -1 and end != -1:
                revised_code = revised_code[start + 9:end].strip()
        elif "```" in revised_code:
            start = revised_code.find("```")
            end = revised_code.find("```", start + 3)
            if start != -1 and end != -1:
                revised_code = revised_code[start + 3:end].strip()
        
        print(f"✅ Claude generated revised code ({len(revised_code)} chars)")
        print(f"📈 Code diff: {len(revised_code) - len(generated_code):+d} characters")
        
        # Update revision attempt counter
        new_attempts = revision_attempts + 1
        
        return {
            **state,
            "generated_code": revised_code,  # Replace with revised code
            "revision_attempts": new_attempts,
            "status": f"Code revised (attempt #{new_attempts}) based on {error_name}"
        }
        
    except Exception as e:
        error_message = f"Failed to revise code with Claude: {str(e)}"
        print(f"❌ {error_message}")
        
        # If revision fails, increment attempts and continue to avoid infinite loop
        revision_attempts = state.get("revision_attempts", 0) + 1
        
        return {
            **state,
            "revision_attempts": revision_attempts,
            "error_log": state.get("error_log", []) + [error_message],
            "status": error_message
        }

def check_execution_result(state: OverallState) -> str:
    """Conditional function to determine next step based on execution success and revision attempts"""
    execution_successful = state.get("execution_successful", False)
    revision_attempts = state.get("revision_attempts", 0)
    max_attempts = state.get("max_revision_attempts", 3)
    
    if execution_successful:
        print("🎯 Code execution successful → Proceeding to write file and git operations")
        return "write_code_to_file"
    elif revision_attempts < max_attempts:
        print(f"⚠️ Code execution failed → Attempting revision ({revision_attempts + 1}/{max_attempts})")
        return "revise_code_with_claude"
    else:
        print(f"❌ Code execution still failing after {max_attempts} revision attempts → Writing file locally and cleanup")
        return "write_code_to_file_local_only"

# Step 5a: Write code to file (full process - for successful execution)
def write_code_to_file(state: OverallState) -> OverallState:
    """Write code to file in sandbox (for successful execution - will proceed to git operations)"""
    # This is the existing function but simplified for the git flow
    return write_code_to_file_base(state, for_git_operations=True)

# Step 5b: Write code to file (local only - for failed execution) 
def write_code_to_file_local_only(state: OverallState) -> OverallState:
    """Write code to local file only (for failed execution - will skip git operations)"""
    return write_code_to_file_base(state, for_git_operations=False)

def write_code_to_file_base(state: OverallState, for_git_operations: bool = True) -> OverallState:
    """Base function to write generated code to file(s)"""
    try:
        sandbox = state.get("sandbox")
        repo_path = state.get("repo_path")
        generated_code = state.get("generated_code")
        
        # Validate required inputs
        if not generated_code:
            raise ValueError("No generated code available")
        if len(generated_code.strip()) == 0:
            raise ValueError("Generated code is empty")
        
        print("💾 Writing generated code...")
        print(f"📝 Code length: {len(generated_code)} characters")
        
        local_file_path = None
        
        # Always handle local download if requested
        should_download = state.get("download", False)
        if should_download:
            print("\n📥 Saving file locally...")
            try:
                # Create output directory
                output_dir = os.path.join(".", "tests", "output")
                os.makedirs(output_dir, exist_ok=True)
                print(f"📁 Created/verified output directory: {output_dir}")
                
                # Create local filename with timestamp
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                local_filename = os.path.join(output_dir, f"generated_graph_{timestamp}.py")
                
                # Write to local file
                with open(local_filename, 'w', encoding='utf-8') as f:
                    f.write(generated_code)
                
                local_file_path = os.path.abspath(local_filename)
                print(f"✅ Downloaded to local file: {local_file_path}")
                
            except Exception as download_error:
                print(f"⚠️ Local download failed: {download_error}")
        
        # For git operations, write to sandbox with proper structure (only if not already written)
        if for_git_operations and sandbox and repo_path:
            # Check if file was already written during LangGraph dev testing
            if state.get("code_written", False) and state.get("langgraph_dev_tested", False):
                print(f"📄 File structure already created during LangGraph dev testing")
            else:
                print(f"📄 Writing to sandbox with src/agent/ structure...")
                try:
                    # Create src/agent directory structure
                    src_dir = f"{repo_path}/src"
                    agent_dir = f"{repo_path}/src/agent"
                    
                    print("📁 Creating src/agent/ directory structure...")
                    
                    # Write __init__.py file (only in agent package)
                    sandbox.files.write(f"{agent_dir}/__init__.py", "# agent package") 
                    
                    # Write the main graph.py file
                    graph_file_path = f"{agent_dir}/graph.py"
                    write_result = sandbox.files.write(graph_file_path, generated_code)
                    print(f"✅ src/agent/graph.py and package structure written to sandbox successfully")
                    
                except Exception as write_error:
                    print(f"⚠️ Sandbox file write failed: {write_error}")
                    # Continue - local file was saved
        
        status_msg = "Code written successfully"
        if local_file_path:
            status_msg += f" (local: {local_file_path})"
        if for_git_operations:
            status_msg += " (ready for git operations)"
        
        return {
            **state,
            "code_written": True,
            "local_file_path": local_file_path,
            "status": status_msg
        }
        
    except Exception as e:
        error_message = f"Failed to write code: {str(e)}"
        print(f"❌ {error_message}")
        return {
            **state,
            "code_written": False,
            "error_log": state.get("error_log", []) + [error_message],
            "status": error_message
        }

# Helper function for detecting merge conflicts (supports multiple files)
def detect_merge_conflict_markers(sandbox, repo_path: str, file_paths: list = None) -> dict:
    """Detect if files contain merge conflict markers"""
    if file_paths is None:
        file_paths = ["src/agent/graph.py"]  # Default to new structure
    
    conflicts = {}
    
    for file_path in file_paths:
        try:
            full_path = f"{repo_path}/{file_path}"
            
            # Skip if file doesn't exist (might be normal for .env or langgraph.json)
            try:
                file_content = sandbox.files.read(full_path)
            except:
                print(f"ℹ️ File {file_path} doesn't exist in repo (normal for new files)")
                conflicts[file_path] = False
                continue
            
            # Check for merge conflict markers (more precise detection)
            lines = file_content.split('\n')
            has_conflicts = False
            
            for line in lines:
                line_stripped = line.strip()
                # Only detect actual Git conflict markers - must be exactly at line start without comments
                if (line_stripped.startswith('<<<<<<< ') or  # Note: space after to avoid false positives
                    line_stripped == '=======' or           # Must be exact match
                    line_stripped.startswith('>>>>>>> ')):  # Note: space after to avoid false positives
                    has_conflicts = True
                    break
            
            conflicts[file_path] = has_conflicts
            
            if has_conflicts:
                print(f"⚠️ Merge conflict markers detected in {file_path}")
                # Show first few lines containing conflict markers for debugging
                conflict_lines = []
                for line in lines[:20]:
                    line_stripped = line.strip()
                    if (line_stripped.startswith('<<<<<<< ') or 
                        line_stripped == '=======' or 
                        line_stripped.startswith('>>>>>>> ')):
                        conflict_lines.append(line)
                        if len(conflict_lines) >= 3:
                            break
                if conflict_lines:
                    print(f"   Conflict markers found: {conflict_lines}")
            
        except Exception as e:
            print(f"⚠️ Could not check {file_path} for conflict markers: {e}")
            conflicts[file_path] = False
    
    return conflicts

def resolve_merge_conflicts_automatically(sandbox, repo_path: str, file_content_map: dict) -> bool:
    """Automatically resolve merge conflicts by using our clean content"""
    try:
        all_resolved = True
        
        for file_path, content in file_content_map.items():
            if content is None:
                continue  # Skip files without content to resolve
                
            full_path = f"{repo_path}/{file_path}"
            
            print(f"🔧 Auto-resolving merge conflicts in {file_path}...")
            
            # Overwrite with our clean content
            sandbox.files.write(full_path, content)
            
            print(f"✅ Overrode conflicted {file_path} with clean content")
        
        return all_resolved
        
    except Exception as e:
        print(f"❌ Failed to auto-resolve conflicts: {e}")
        return False

# Step 6: Git operations (checkout, commit, push)
def git_operations(state: OverallState) -> OverallState:
    """Handle git checkout, commit, and push operations with conflict resolution"""
    try:
        sandbox = state.get("sandbox")
        repo_path = state.get("repo_path")
        branch_name = state.get("branch_name")
        
        if not sandbox or not repo_path:
            raise ValueError("Sandbox or repository path not available")
        
        print("🔧 Starting git operations...")
        
        # Configure git identity first (required for commits)
        print("🔧 Configuring git identity...")
        git_email = os.getenv("GIT_EMAIL", "automation@langgraph-workflow.com")  
        git_name = os.getenv("GIT_NAME", "LangGraph Workflow Bot")
        
        # Set git config in the repository (not global)
        config_commands = [
            f"cd {repo_path} && git config user.email '{git_email}'",
            f"cd {repo_path} && git config user.name '{git_name}'",
            f"cd {repo_path} && git config pull.rebase false"  # Use merge strategy for divergent branches
        ]
        
        for cmd in config_commands:
            result = sandbox.commands.run(cmd)
            if result.exit_code != 0:
                print(f"⚠️ Git config failed: {result.stderr}")
                raise ValueError(f"Failed to configure git identity: {result.stderr}")
        
        print(f"✅ Git configured: {git_name} <{git_email}> (merge strategy for divergent branches)")
        
        # Generate branch name if not provided
        if not branch_name:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = f"generated-graph-{timestamp}"
        
        print(f"📌 Using branch: {branch_name}")
        
        # Change to repo directory and perform git operations
        # First try to checkout existing branch, if that fails create new one
        checkout_cmd = f"cd {repo_path} && git checkout {branch_name} 2>/dev/null || git checkout -b {branch_name}"
        
        print(f"🔧 Running: git checkout (existing) or create branch")
        checkout_result = sandbox.commands.run(checkout_cmd)
        
        if checkout_result.exit_code != 0:
            raise ValueError(f"Git checkout/create branch failed: {checkout_result.stderr}")
        
        print(f"✅ Branch '{branch_name}' ready")
        
        # Track whether we made a temporary commit during pull
        made_temp_commit = False
        
        # Proactively pull any remote changes to avoid non-fast-forward errors later
        print(f"🔄 Proactively pulling remote changes...")
        try:
            # First, check if we have an untracked graph.py that might conflict
            status_cmd = f"cd {repo_path} && git status --porcelain"
            status_result = sandbox.commands.run(status_cmd)
            
            if status_result.exit_code == 0 and "graph.py" in status_result.stdout:
                print(f"📄 Found untracked graph.py - committing it before pull to avoid conflicts")
                # Add and commit the file to prevent merge conflicts
                add_cmd = f"cd {repo_path} && git add graph.py"
                add_result = sandbox.commands.run(add_cmd)
                if add_result.exit_code != 0:
                    print(f"⚠️ Failed to stage graph.py: {add_result.stderr}")
                else:
                    # Generate a temporary commit message
                    temp_commit_msg = "temp: stage graph.py for pull"
                    commit_cmd = f'cd {repo_path} && git commit -m "{temp_commit_msg}"'
                    commit_result = sandbox.commands.run(commit_cmd)
                    if commit_result.exit_code == 0:
                        print(f"✅ Committed graph.py temporarily for clean pull")
                        made_temp_commit = True
                    else:
                        print(f"⚠️ Failed to commit graph.py: {commit_result.stderr}")
            
            # Use explicit merge strategy for divergent branches with auto-commit
            pull_cmd = f"cd {repo_path} && git pull --no-rebase --commit origin {branch_name}"
            pull_result = sandbox.commands.run(pull_cmd)
            
            if pull_result.exit_code == 0:
                print(f"✅ Pulled remote changes successfully")
            else:
                # Check if it's just a "couldn't find remote ref" (new branch)
                pull_error_str = pull_result.stderr or ""
                if "couldn't find remote ref" in pull_error_str or "does not exist" in pull_error_str:
                    print(f"📌 Remote branch doesn't exist yet - this is normal for new branches")
                elif "divergent branches" in pull_error_str or "Need to specify how to reconcile" in pull_error_str:
                    print(f"⚠️ Divergent branches detected - trying merge strategy")
                    # Try explicit merge
                    merge_pull_cmd = f"cd {repo_path} && git pull --strategy=ours origin {branch_name}"
                    merge_result = sandbox.commands.run(merge_pull_cmd)
                    if merge_result.exit_code == 0:
                        print(f"✅ Merged divergent branches successfully")
                    else:
                        print(f"⚠️ Merge strategy also failed: {merge_result.stderr}")
                else:
                    print(f"⚠️ Pull failed but continuing: {pull_error_str}")
                    # Check if we're now in a merge state that needs completion
                    merge_head_cmd = f"cd {repo_path} && test -f .git/MERGE_HEAD"
                    if sandbox.commands.run(merge_head_cmd).exit_code == 0:
                        print(f"🔄 Pull left us in merge state - will handle during commit phase")
            
            # Critical: Check for merge conflict markers after any pull/merge operation
            print(f"🔍 Checking for merge conflict markers in generated files...")
            files_to_check = ["src/agent/graph.py", "src/agent/__init__.py", ".env", "langgraph.json", "requirements.txt"]
            conflicts = detect_merge_conflict_markers(sandbox, repo_path, files_to_check)
            
            if any(conflicts.values()):
                print(f"⚠️ Merge conflicts detected - auto-resolving with our generated content...")
                
                # Prepare content map for conflict resolution
                generated_code = state.get("generated_code", "")
                
                # Get the .env content from sandbox (already created)
                try:
                    env_content = sandbox.files.read(f"{repo_path}/.env")
                except:
                    env_content = None
                
                # Get the langgraph.json content from sandbox (already created)
                try:
                    langgraph_content = sandbox.files.read(f"{repo_path}/langgraph.json")
                except:
                    langgraph_content = None
                
                # Get the requirements.txt content (from template)
                try:
                    template_path = os.path.join(os.path.dirname(__file__), "requirements_template.txt")
                    if os.path.exists(template_path):
                        with open(template_path, 'r', encoding='utf-8') as f:
                            requirements_content = f.read()
                    else:
                        requirements_content = None
                except:
                    requirements_content = None
                
                file_content_map = {
                    "src/agent/graph.py": generated_code if generated_code else None,
                    "src/agent/__init__.py": "# agent package",
                    ".env": env_content,
                    "langgraph.json": langgraph_content,
                    "requirements.txt": requirements_content
                }
                
                if resolve_merge_conflicts_automatically(sandbox, repo_path, file_content_map):
                    print(f"✅ Merge conflicts resolved automatically")
                else:
                    print(f"❌ Failed to auto-resolve conflicts - aborting git operations")
                    raise ValueError("Merge conflicts could not be resolved automatically")
                    
        except Exception as pull_error:
            pull_error_str = str(pull_error)
            if "couldn't find remote ref" in pull_error_str or "does not exist" in pull_error_str:
                print(f"📌 Remote branch doesn't exist yet - this is normal for new branches")
            else:
                print(f"⚠️ Pull exception: {pull_error}")
                print(f"   Continuing anyway...")
                # Check if exception left us in a merge state
                try:
                    merge_head_cmd = f"cd {repo_path} && test -f .git/MERGE_HEAD"
                    if sandbox.commands.run(merge_head_cmd).exit_code == 0:
                        print(f"🔄 Pull exception left us in merge state - will handle during commit phase")
                except:
                    pass
        
        # Copy requirements_template.txt to requirements.txt in the target repo
        print("📦 Copying requirements_template.txt to requirements.txt...")
        try:
            # Read the local requirements_template.txt
            template_path = os.path.join(os.path.dirname(__file__), "requirements_template.txt")
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    requirements_content = f.read()
                
                # Write requirements.txt to the sandbox repo
                requirements_file_path = f"{repo_path}/requirements.txt"
                sandbox.files.write(requirements_file_path, requirements_content)
                print("✅ requirements.txt copied successfully to target repository")
            else:
                print("⚠️ requirements_template.txt not found, skipping requirements.txt creation")
        except Exception as req_error:
            print(f"⚠️ Failed to copy requirements.txt: {req_error}")
            # Continue anyway - this is not critical for the workflow
        
        # Add all generated files (src/agent/graph.py, src/agent/__init__.py, .env, langgraph.json, requirements.txt)  
        print(f"🔧 Staging generated files (src/agent/graph.py, src/agent/__init__.py, .env, langgraph.json, requirements.txt)...")
        files_to_add = ["src/", ".env", "langgraph.json", "requirements.txt"]  # Stage entire src/ directory for simplicity
        
        for file_name in files_to_add:
            add_cmd = f"cd {repo_path} && git add {file_name}"
            add_result = sandbox.commands.run(add_cmd)
            
            if add_result.exit_code != 0:
                print(f"⚠️ Failed to add {file_name}: {add_result.stderr}")
                # Don't fail completely - some files might not exist yet
            else:
                print(f"✅ {file_name} staged for commit")
        
        # Final check for merge conflicts before committing
        print(f"🔍 Final check for merge conflict markers before commit...")
        files_to_check = ["src/agent/graph.py", "src/agent/__init__.py", ".env", "langgraph.json", "requirements.txt"]
        conflicts = detect_merge_conflict_markers(sandbox, repo_path, files_to_check)
        
        if any(conflicts.values()):
            print(f"⚠️ Merge conflicts still detected before commit - auto-resolving...")
            
            # Prepare content map for final conflict resolution
            generated_code = state.get("generated_code", "")
            
            # Get current .env and langgraph.json content
            try:
                env_content = sandbox.files.read(f"{repo_path}/.env")
            except:
                env_content = None
            
            try:
                langgraph_content = sandbox.files.read(f"{repo_path}/langgraph.json")
            except:
                langgraph_content = None
            
            # Get the requirements.txt content (from template)
            try:
                template_path = os.path.join(os.path.dirname(__file__), "requirements_template.txt")
                if os.path.exists(template_path):
                    with open(template_path, 'r', encoding='utf-8') as f:
                        requirements_content = f.read()
                else:
                    requirements_content = None
            except:
                requirements_content = None
            
            file_content_map = {
                "src/agent/graph.py": generated_code if generated_code else None,
                "src/agent/__init__.py": "# agent package",
                ".env": env_content,
                "langgraph.json": langgraph_content,
                "requirements.txt": requirements_content
            }
            
            if resolve_merge_conflicts_automatically(sandbox, repo_path, file_content_map):
                print(f"✅ Final merge conflicts resolved")
                # Re-stage files after conflict resolution
                for file_name in files_to_add:
                    add_cmd = f"cd {repo_path} && git add {file_name}"
                    add_result = sandbox.commands.run(add_cmd)
                    if add_result.exit_code == 0:
                        print(f"✅ Conflict-resolved {file_name} re-staged")
            else:
                print(f"❌ Failed to resolve conflicts before commit - aborting")
                raise ValueError("Cannot commit files with merge conflict markers")
        
        # Check if we need to make a new commit (or if we already made a temporary one)
        if made_temp_commit:
            print("📝 Temporary commit was made during pull - handling post-merge state")
            
            # Check if we're in the middle of a merge
            merge_head_cmd = f"cd {repo_path} && test -f .git/MERGE_HEAD"
            print(f"🔧 Checking merge state: {merge_head_cmd}")
            merge_check = sandbox.commands.run(merge_head_cmd)
            print(f"📊 Merge check result: exit_code={merge_check.exit_code}")
            
            if merge_check.exit_code == 0:  # We are in a merge
                print("🔄 Completing merge in progress...")
                
                # Generate commit message for the merge
                print("🤖 Generating commit message with Claude...")
                commit_message = generate_commit_message_with_claude(state)
                
                # Complete the merge with our commit message
                merge_commit_cmd = f'cd {repo_path} && git commit -m "{commit_message}"'
                print(f"🔧 Running: {merge_commit_cmd}")
                merge_result = sandbox.commands.run(merge_commit_cmd)
                print(f"📊 Merge commit result: exit_code={merge_result.exit_code}, stderr='{merge_result.stderr}', stdout='{merge_result.stdout}'")
                
                if merge_result.exit_code != 0:
                    raise ValueError(f"Git merge completion failed: {merge_result.stderr}")
                
                print(f"✅ Merge completed with message: {commit_message}")
                
            else:
                # No active merge, we can amend normally
                print("🤖 Generating commit message with Claude...")
                commit_message = generate_commit_message_with_claude(state)
                
                # Amend the temporary commit with the proper message
                amend_cmd = f'cd {repo_path} && git commit --amend -m "{commit_message}"'
                print(f"🔧 Running: {amend_cmd}")
                commit_result = sandbox.commands.run(amend_cmd)
                print(f"📊 Amend commit result: exit_code={commit_result.exit_code}, stderr='{commit_result.stderr}', stdout='{commit_result.stdout}'")
                
                if commit_result.exit_code != 0:
                    raise ValueError(f"Git commit amend failed: {commit_result.stderr}")
                
                print(f"✅ Amended commit with message: {commit_message}")
            
        else:
            # Normal commit flow
            # Check if there are changes to commit
            status_cmd = f"cd {repo_path} && git diff --cached --quiet"
            print(f"🔧 Checking for staged changes: {status_cmd}")
            
            try:
                status_result = sandbox.commands.run(status_cmd)
                print(f"📊 Staged changes check: exit_code={status_result.exit_code}, stderr='{status_result.stderr}', stdout='{status_result.stdout}'")
                
                if status_result.exit_code == 0:
                    print("⚠️ No changes detected - skipping commit")
                    return {
                        **state,
                        "git_branch": branch_name,
                        "commit_message": "No changes to commit",
                        "git_pushed": False,
                        "status": f"No changes detected in branch: {branch_name}"
                    }
                elif status_result.exit_code == 1:
                    print("✅ Changes detected - proceeding with commit")
                else:
                    # Some other error occurred
                    print(f"⚠️ Unexpected exit code from git diff: {status_result.exit_code}")
                    print(f"   stderr: '{status_result.stderr}', stdout: '{status_result.stdout}'")
                    print("   Proceeding anyway...")
                    
            except Exception as diff_error:
                # E2B raises exception for exit code 1, but this is expected for git diff --cached --quiet
                error_str = str(diff_error)
                print(f"📊 Exception during diff check: {error_str}")
                if "exited with code 1" in error_str:
                    print("✅ Changes detected (E2B treated exit code 1 as error, but this is normal)")
                    print("   Proceeding with commit...")
                else:
                    print(f"⚠️ Unexpected error checking staged changes: {diff_error}")
                    print("   Proceeding anyway...")
            
            # Generate commit message with Claude
            print("🤖 Generating commit message with Claude...")
            commit_message = generate_commit_message_with_claude(state)
            
            # Commit changes
            commit_cmd = f'cd {repo_path} && git commit -m "{commit_message}"'
            print(f"🔧 Running: {commit_cmd}")
            commit_result = sandbox.commands.run(commit_cmd)
            print(f"📊 Commit result: exit_code={commit_result.exit_code}, stderr='{commit_result.stderr}', stdout='{commit_result.stdout}'")
            
            if commit_result.exit_code != 0:
                raise ValueError(f"Git commit failed: {commit_result.stderr}")
            
            print(f"✅ Committed with message: {commit_message}")
        
        # Push to remote (if configured)
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            # Configure git with token for push
            repo_url = state["target_repo_url"]
            if not repo_url.startswith("http"):
                # Convert to HTTPS URL with token
                if "/" in repo_url:
                    owner_repo = repo_url
                    push_url = f"https://{github_token}@github.com/{owner_repo}"
                else:
                    raise ValueError(f"Invalid repo URL format: {repo_url}")
            else:
                push_url = repo_url.replace("https://", f"https://{github_token}@")
            
            # Set remote URL
            remote_cmd = f"cd {repo_path} && git remote set-url origin {push_url}"
            print(f"🔧 Setting remote URL...")
            remote_result = sandbox.commands.run(remote_cmd)
            
            if remote_result.exit_code != 0:
                print(f"⚠️ Failed to set remote URL: {remote_result.stderr}")
            else:
                print(f"✅ Remote URL configured")
                
                # Push should work cleanly now since we pulled proactively
                push_cmd = f"cd {repo_path} && git push origin {branch_name}"
                print(f"🔧 Pushing to remote branch...")
                
                try:
                    push_result = sandbox.commands.run(push_cmd)
                    print(f"✅ Pushed to remote branch: {branch_name}")
                    
                except Exception as push_error:
                    push_error_str = str(push_error)
                    print(f"⚠️ Push failed: {push_error_str}")
                    
                    # Since we already pulled, if push still fails, try force push as fallback
                    print(f"🔧 Trying force push as fallback...")
                    try:
                        force_push_cmd = f"cd {repo_path} && git push --force origin {branch_name}"
                        force_result = sandbox.commands.run(force_push_cmd)
                        print(f"✅ Force pushed to remote branch: {branch_name}")
                        print(f"⚠️ Note: Used force push - remote history may have been overwritten")
                        
                    except Exception as force_error:
                        print(f"❌ Force push also failed: {force_error}")
                        raise force_error
        
        return {
            **state,
            "git_branch": branch_name,
            "commit_message": commit_message,
            "git_pushed": True,
            "status": f"Git operations completed - Branch: {branch_name} (includes deployment files: src/agent/graph.py, .env, langgraph.json, requirements.txt)"
        }
        
    except Exception as e:
        error_message = f"Git operations failed: {str(e)}"
        print(f"❌ {error_message}")
        print(f"🔍 Exception details: {type(e).__name__}: {e}")
        
        # Get current branch for debugging
        try:
            branch_result = sandbox.commands.run(f"cd {repo_path} && git branch --show-current")
            current_branch = branch_result.stdout.strip() if branch_result.exit_code == 0 else "unknown"
            print(f"📍 Current git branch: {current_branch}")
        except:
            print("📍 Could not determine current branch")
        
        return {
            **state,
            "git_branch": branch_name if 'branch_name' in locals() else None,
            "commit_message": None, 
            "git_pushed": False,
            "error_log": state.get("error_log", []) + [error_message],
            "status": error_message
        }

def generate_commit_message_with_claude(state: OverallState) -> str:
    """Generate a commit message using Claude"""
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        
        client = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            max_tokens=1000,
            temperature=0
        )
        
        input_json = state.get("input_json", {})
        generated_code = state.get("generated_code", "")
        execution_result = state.get("result", "")
        
        prompt = f"""Generate a concise, professional git commit message for a LangGraph agent that was automatically generated with deployment configuration.

Context:
- Target specification: {json.dumps(input_json, indent=2)}
- Generated files: src/agent/graph.py (LangGraph workflow), langgraph.json (config), .env (environment), src/agent/__init__.py
- Generated code: {generated_code if generated_code else "No code"}...
- Execution result: {execution_result[:200] if execution_result else "No output"}...
- Generated code successfully executes with proper package structure

Requirements:
- Use conventional commit format (e.g., "feat:", "fix:", "chore:")
- Be concise (60 characters or less for the subject)
- Mention it's auto-generated with deployment config
- Focus on what the agent does, not how it was created

Examples:
- "feat: add credit report analysis workflow + deploy config"
- "feat: implement multi-step data processing agent + config"
- "chore: auto-generate workflow agent with deployment files"

Generate only the commit message, nothing else:"""

        messages = [
            ("human", prompt)
        ]
        response = client.invoke(messages)
        
        commit_message = response.content
        
        # Clean up the commit message
        commit_message = commit_message.strip().replace('"', "'")
        
        if not commit_message:
            commit_message = "feat: auto-generated LangGraph workflow"
        
        return commit_message
        
    except Exception as e:
        print(f"⚠️ Failed to generate commit message with Claude: {e}")
        return "feat: auto-generated LangGraph workflow"

# Step n: Cleanup sandbox  
def cleanup_sandbox(state: OverallState) -> OverallState:
    """Clean up the E2B sandbox"""
    try:
        sandbox = state.get("sandbox")
        if sandbox:
            sandbox.kill()
            print("✅ Sandbox cleaned up successfully")
        
        # Determine overall success
        execution_successful = state.get("execution_successful", False)
        code_written = state.get("code_written", False)
        git_pushed = state.get("git_pushed", False)
        
        if execution_successful and code_written and git_pushed:
            success = True
            final_status = "Workflow completed successfully with git operations"
        elif execution_successful and code_written:
            success = True  
            final_status = "Workflow completed successfully (local save only)"
        elif code_written:
            success = False
            final_status = "Workflow completed with errors (code saved locally)"
        else:
            success = False
            final_status = "Workflow failed"
        
        return {
            **state,
            "sandbox": None,
            "success": success,
            "status": final_status
        }
        
    except Exception as e:
        error_message = f"Cleanup failed: {str(e)}"
        print(f"❌ {error_message}")
        return {
            **state,
            "sandbox": None,
            "success": False,
            "error_log": state.get("error_log", []) + [error_message],
            "status": error_message
        }


def build_modular_graph():
    """Build the modular graph with controlled steps and conditional flow"""
    builder = StateGraph(OverallState, input_schema=InputState, output_schema=OutputState)
    
    # Add nodes for each step
    builder.add_node("create_sandbox", create_sandbox)
    builder.add_node("clone_repository", clone_repository_with_token)
    builder.add_node("generate_code_with_claude", generate_code_with_claude)
    builder.add_node("run_code", run_code)
    
    # Code revision (for failed executions)
    builder.add_node("revise_code_with_claude", revise_code_with_claude)
    
    # Conditional write nodes
    builder.add_node("write_code_to_file", write_code_to_file)  # For successful execution
    builder.add_node("write_code_to_file_local_only", write_code_to_file_local_only)  # For failed execution
    
    # Git operations (only for successful execution)
    builder.add_node("git_operations", git_operations)
    
    # Cleanup
    builder.add_node("cleanup_sandbox", cleanup_sandbox)
    
    # Add sequential edges up to run_code
    builder.add_edge(START, "create_sandbox")
    builder.add_edge("create_sandbox", "clone_repository")
    builder.add_edge("clone_repository", "generate_code_with_claude")
    builder.add_edge("generate_code_with_claude", "run_code")
    
    # Add conditional edges based on execution success and revision attempts
    builder.add_conditional_edges(
        "run_code",
        check_execution_result,
        {
            "write_code_to_file": "write_code_to_file",                     # Success path
            "revise_code_with_claude": "revise_code_with_claude",           # Revision path
            "write_code_to_file_local_only": "write_code_to_file_local_only" # Final failure path
        }
    )
    
    # Revision loop: revise_code_with_claude → run_code (try again)
    builder.add_edge("revise_code_with_claude", "run_code")
    
    # Success path: write_code_to_file → git_operations → cleanup
    builder.add_edge("write_code_to_file", "git_operations")
    builder.add_edge("git_operations", "cleanup_sandbox")
    
    # Failure path: write_code_to_file_local_only → cleanup (skip git)
    builder.add_edge("write_code_to_file_local_only", "cleanup_sandbox")
    
    # Final step
    builder.add_edge("cleanup_sandbox", END)
    
    return builder.compile()

# Create the graph instance
graph = build_modular_graph()

if __name__ == "__main__":
    print("Modular LangGraph Agent Workflow - graph5.py")
    print("Features: Controlled steps with E2B + Claude")
    print("Steps: Sandbox → Clone → Generate → Write → Cleanup")
    
    # Example usage
    example_input = {
        "input_json": {
            "workflow": "example", 
            "steps": ["step1", "step2"],
            "output": "generated"
        },
        "target_repo_url": "https://github.com/your-org/your-repo.git",
        "download": True,
        "os_url": "http://localhost:8080"  # Optional: OS URL for agent connection
    }
    
    print(f"\nExample input: {json.dumps(example_input, indent=2)}")
    print("\nTo use: graph.invoke(example_input)")
