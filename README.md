# FINTOR - LangGraph Agent Generator

A robust, modular LangGraph agent generation workflow that replaces the buggy VibeKit library with a controlled, step-by-step approach using E2B sandboxes and Claude AI.

## What is This Project?

This project provides a comprehensive LangGraph agent generation system that:
- Generates LangGraph workflows from JSON specifications
- Tests and validates generated code in isolated E2B sandboxes  
- Automatically handles git operations (clone, commit, push)
- Provides intelligent code revision using Claude AI
- Offers complete control and debugging at each step

## Project Structure

```
FINTOR/
├── graph5.py                         # 🎯 Main modular LangGraph workflow
├── example_graph5_usage.py          # 📖 Usage examples and testing
├── test_graph5.py                   # 🧪 Unit tests for workflow components
├── prompts/
│   ├── base_09-04-25_v3.md          # 🤖 Claude prompt template for code generation
│   └── ...                          # Other prompt variations
├── tests/
│   ├── input/
│   │   └── credit_report.json       # 📋 Sample JSON specifications
│   └── output/                      # 📁 Generated code outputs (local downloads)
├── langgraph_template.json          # ⚙️ LangGraph configuration template
├── archive/                          # 🗄️ Old VibeKit files (archived)
├── .env                             # 🔐 Environment variables
└── README.md
```

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install langchain-anthropic e2b-code-interpreter langgraph python-dotenv
   ```

2. **Configure environment variables:**
   Create a `.env` file with the following required variables:
   ```env
   # Required API Keys
   ANTHROPIC_API_KEY=your-anthropic-api-key
   GITHUB_TOKEN=your-github-token
   LANGSMITH_API_KEY=your-langsmith-api-key
   
   # Required Paths
   PROMPT_PATH=./prompts/base_09-04-25_v3.md
   TEMPLATE_CODE_PATH=./path/to/your/template.py
   
   # Optional Configuration
   TARGET_GITHUB_REPO=YourOrg/your-repo.git
   GIT_EMAIL=your-email@example.com
   GIT_NAME=Your Name
   ```

3. **Test the installation:**
   ```bash
   python test_graph5.py
   ```

## Usage

### Quick Start
```bash
python example_graph5_usage.py
```

### Manual Workflow Execution
```python
from graph5 import graph

# Define your workflow input
workflow_input = {
    "input_json": {
        "workflow": "credit_report_analysis",
        "steps": [
            {"action": "navigate", "target": "credit_portal"},
            {"action": "input", "field": "borrower_name"},
            {"action": "screenshot", "description": "capture_report"}
        ]
    },
    "target_repo_url": "YourOrg/your-repo.git",
    "download": True,
    "branch_name": "auto-generated-workflow",
    "max_revision_attempts": 3
}

# Execute the workflow
result = graph.invoke(workflow_input)
print(f"Success: {result['success']}")
print(f"Generated code: {result['generated_code'][:200]}...")
```

### Workflow Steps

The modular workflow executes these steps automatically:

1. **🔧 Create E2B Sandbox** - Isolated execution environment
2. **📥 Clone Repository** - Clone target GitHub repo with token auth
3. **🤖 Generate Code** - Use Claude to generate LangGraph workflow from JSON spec
4. **🔄 Enhanced Validation**:
   - Phase 1: Basic script execution with auto-package installation
   - Phase 2: Setup langgraph.json + .env configuration  
   - Phase 3: LangGraph dev startup validation
5. **🎯 Intelligent Revision** - If validation fails, Claude revises code (max 3 attempts)
6. **📁 File Operations** - Write to sandbox + optional local download
7. **🔧 Git Operations** - Checkout branch, proactive pull, commit deployment files (src/agent/graph.py, src/agent/__init__.py, .env, langgraph.json), push
8. **🧹 Cleanup** - Terminate sandbox

## Key Features

### 🤖 **AI-Powered Code Generation**
- **Claude Sonnet 4**: Latest Anthropic model for high-quality LangGraph code generation
- **Intelligent Prompting**: Sophisticated prompt templates with dynamic variable injection
- **Template-Guided**: Uses template code structure for consistent output

### 🔄 **Robust Validation & Revision**
- **Two-Phase Validation**: Basic execution + LangGraph dev server testing
- **Auto-Package Installation**: Detects and installs required Python packages
- **Smart Revision Loop**: Claude analyzes failures and revises code (up to 3 attempts)
- **Differentiated Prompts**: Different revision strategies for execution vs LangGraph dev errors

### 🔧 **Advanced Git Integration**
- **Proactive Conflict Resolution**: Handles divergent branches with merge strategies
- **Smart Conflict Detection**: Automatically detects and resolves merge conflict markers
- **Clean Code Commits**: Prevents committing files with conflict markers
- **Smart Commit Management**: Detects merge states and handles amend vs merge commits
- **Auto-Generated Messages**: Claude creates meaningful commit messages
- **Token Authentication**: Secure GitHub integration with personal access tokens

### 🏖️ **E2B Sandbox Environment**
- **Isolated Execution**: Safe code testing in containerized environment
- **Real Package Testing**: Actual pip installations and imports
- **Git Operations**: Full git workflow within sandbox
- **Environment Setup**: Automated langgraph.json and .env configuration

## Configuration Options

### Input Parameters
```python
{
    "input_json": dict,              # JSON workflow specification
    "target_repo_url": str,          # GitHub repo URL (owner/repo.git)
    "download": bool,                # Download generated code locally
    "branch_name": str,              # Git branch name (optional)
    "max_revision_attempts": int     # Max code revision attempts (default: 3)
}
```

### Environment Variables
```env
# Required
ANTHROPIC_API_KEY=                   # Claude API access
GITHUB_TOKEN=                        # GitHub repo access  
LANGSMITH_API_KEY=                   # LangSmith integration
PROMPT_PATH=                         # Path to prompt template
TEMPLATE_CODE_PATH=                  # Path to template code

# Optional
GIT_EMAIL=                           # Git commit author email
GIT_NAME=                            # Git commit author name
TARGET_GITHUB_REPO=                  # Default target repository
OPENAI_API_KEY=                      # If using OpenAI models
```

## Key Benefits

- 🎯 **Modular & Controllable** - Each step is isolated and debuggable
- 🛡️ **Error Recovery** - Intelligent revision system handles failures gracefully
- 🔄 **Complete Automation** - End-to-end workflow from JSON spec to deployed code
- 🧪 **Thorough Testing** - Real execution validation, not just syntax checking
- 🌿 **Git-Safe** - Proactive conflict resolution prevents force pushes
- 📊 **Detailed Reporting** - Comprehensive status tracking and error reporting
- ⚡ **Fast Iteration** - Quick feedback loop for code generation improvements
- 🚀 **Deployment Ready** - Automatically generates proper Python package structure (src/agent/), .env and langgraph.json for LangGraph Cloud deployment

## Getting API Keys

### Required API Keys

1. **Anthropic API Key** - Get your API key from [https://console.anthropic.com](https://console.anthropic.com)
   - Sign up for an Anthropic account  
   - Navigate to the API keys section
   - Create a new API key
   - ⚠️ **Usage**: Claude Sonnet 4 for code generation and revision

2. **GitHub Personal Access Token** - Create from [https://github.com/settings/tokens](https://github.com/settings/tokens)
   - Generate a new token (classic)
   - Select scopes: `repo`, `workflow`
   - Copy the token immediately
   - ⚠️ **Usage**: Repository cloning, committing, and pushing

3. **LangSmith API Key** - Get from [https://smith.langchain.com](https://smith.langchain.com)
   - Sign up for a LangSmith account
   - Navigate to settings → API Keys
   - Create a new API key
   - ⚠️ **Usage**: LangGraph dev server validation

### Optional API Keys

4. **E2B API Key** - Get from [https://e2b.dev](https://e2b.dev)
   - Sign up for a free account
   - Navigate to your dashboard
   - Copy your API key
   - ⚠️ **Usage**: Already handled automatically by e2b-code-interpreter package

## Quick Start Guide

1. **Set up environment variables** in `.env` file
2. **Test the installation**: `python test_graph5.py` 
3. **Run example workflow**: `python example_graph5_usage.py`
4. **Create your JSON specification** in `tests/input/` 
5. **Customize the prompt template** in `prompts/`
6. **Deploy your generated workflows** to GitHub repositories

## Advanced Usage

### Custom Prompt Templates
- Modify `prompts/base_09-04-25_v3.md` for different generation styles
- Use `{{INPUT_JSON}}` and `{{TEMPLATE_CODE}}` placeholders
- Test prompt changes with individual workflow runs

### Batch Processing
```python
import json
from graph5 import graph

specifications = [
    json.load(open('tests/input/spec1.json')),
    json.load(open('tests/input/spec2.json')),
    # ... more specs
]

for i, spec in enumerate(specifications):
    result = graph.invoke({
        "input_json": spec,
        "target_repo_url": "YourOrg/your-repo.git", 
        "branch_name": f"batch-generation-{i}",
        "download": True
    })
    print(f"Spec {i}: {'✅' if result['success'] else '❌'}")
```

### LangSmith Cloud Deployment
For cloud deployment, see the comprehensive analysis in the previous conversation about creating cloud-compatible versions that work without E2B dependencies.

## Troubleshooting

### Common Issues

1. **"ANTHROPIC_API_KEY not found"** 
   - Ensure API key is set in `.env` file
   - Check key has sufficient credits and permissions

2. **"Failed to clone repository"**
   - Verify `GITHUB_TOKEN` has `repo` scope
   - Check repository URL format: `owner/repo.git` 
   - Ensure token has access to target repository

3. **"Sandbox creation failed"**
   - E2B service might be temporarily down
   - Check network connectivity
   - Verify account has available sandbox quota

4. **"Git operations failed"**  
   - Ensure `GIT_EMAIL` and `GIT_NAME` are set
   - Check for merge conflicts in target repository
   - Verify branch permissions
   - ✅ **Fixed**: Auto-detection and resolution of merge conflict markers

5. **"LangGraph dev validation failed"**
   - Generated code might have import errors
   - Check if `LANGSMITH_API_KEY` is valid
   - Review generated code structure

### Debug Mode

Enable verbose output by adding debug prints:
```python
import logging
logging.basicConfig(level=logging.INFO)

# Run your workflow - will show detailed step-by-step output
```

### Getting Help

- Check the detailed error logs in workflow output
- Review generated code in `tests/output/` directory  
- Test individual workflow steps using `test_graph5.py`
- Check API service status (Anthropic, E2B, GitHub)
- Verify all environment variables are correctly set

## License

ISC 