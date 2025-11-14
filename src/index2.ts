import { VibeKit } from '@vibe-kit/sdk';

// Extend VibeKit type to include additional methods
// declare module '@vibe-kit/sdk' {
//   interface VibeKit {
//     pushToBranch(): Promise<void>;
//     startSession(): Promise<void>;
//   }
// }
import { createE2BProvider } from '@vibe-kit/e2b';
import { config } from 'dotenv';
import * as fs from 'fs';

// Load environment variables from .env file
config();

// Test prompts for manual testing
const TEST_PROMPTS = {
  simple: "Create a simple hello world function",
  langgraph: `Create a LangGraph agent that implements a basic workflow with two nodes:
    1. Input validation
    2. Data processing
    Show me the complete implementation.`,
  custom: "Your custom prompt here"
} as const;

type TestPromptKey = keyof typeof TEST_PROMPTS;

// Parse command line arguments
const args = process.argv.slice(2);
const mode = args[0] || 'file'; // 'file' or 'test'
const testPrompt = (args[1] || 'simple') as TestPromptKey;

let prompt: string;
if (mode === 'file') {
  const promptFilePath = args[args.indexOf('--prompt-file') + 1];
  if (!promptFilePath) {
    console.error("No prompt file provided. Use: npm run dev -- file --prompt-file <path>");
    console.error("Or use test mode: npm run dev -- test [simple|langgraph|custom]");
    process.exit(1);
  }
  const promptData = JSON.parse(fs.readFileSync(promptFilePath, 'utf-8'));
  prompt = promptData.prompt;
} else {
  prompt = TEST_PROMPTS[testPrompt] || TEST_PROMPTS.simple;
}

console.log("Using prompt mode:", mode);
console.log("Prompt preview:", prompt.substring(0, 100) + "...");

const githubRepoUrl = process.env.TARGET_GITHUB_REPO!;

// Initialize VibeKit
const vibekit = new VibeKit()
  .withAgent({
    type: "claude",
    provider: "anthropic",
    apiKey: process.env.ANTHROPIC_API_KEY!,
    model: "claude-sonnet-4-20250514",
  })
  .withGithub({
    token: process.env.GITHUB_TOKEN!,
    repository: githubRepoUrl,
  })
  .withSandbox(createE2BProvider({
    apiKey: process.env.E2B_API_KEY!,
    templateId: 'vibekit-claude',
  }))
//   .withSession(`session-${Date.now()}`); // Generate unique session ID

console.log('VibeKit initialized successfully!');

// Debug options
const DEBUG_OPTIONS = {
  logFullResponse: true,    // Log the complete response object
  saveToFile: true,        // Save response to a file
  parseMessages: true,     // Parse and display individual messages
  outputPath: './debug'    // Where to save debug files
};

// Ensure debug directory exists
if (DEBUG_OPTIONS.saveToFile) {
  if (!fs.existsSync(DEBUG_OPTIONS.outputPath)) {
    fs.mkdirSync(DEBUG_OPTIONS.outputPath, { recursive: true });
  }
}

// Main function to handle code generation and GitHub operations
async function main() {
  try {
    console.log('Starting sandbox session...');
    
    // // Initialize sandbox session
    // await vibekit.startSession();
    
    try {
      console.log('Generating code...');
      console.log('Using prompt:', prompt);

      // First generate code in a feature branch
      console.log('Generating code in feature branch...');
      await vibekit.generateCode({
        prompt: prompt,
        mode: 'code',
        // branch: 'feature/generated-code'
      });

    //   // Save debug info if enabled
    //   if (DEBUG_OPTIONS.saveToFile) {
    //     const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    //     const debugFile = `${DEBUG_OPTIONS.outputPath}/debug_${timestamp}.json`;
    //     fs.writeFileSync(debugFile, JSON.stringify(result, null, 2));
    //     console.log(`Debug info saved to: ${debugFile}`);
    //   }

      // Then push changes to the main branch
      console.log('Pushing changes to GitHub...');
      await vibekit.createPullRequest();
      console.log('Successfully pushed changes to GitHub');

      // return result;
    } finally {
      // Always cleanup the sandbox session
      console.log('Cleaning up sandbox session...');
      try {
        await vibekit.kill();
        console.log('Sandbox session cleaned up successfully');
      } catch (cleanupError) {
        console.warn('Warning: Failed to cleanup sandbox:', cleanupError);
      }
    }
  } catch (err) {
    const error = err as Error;
    console.error('Error:', error.message);
    
    // Save error details if debug is enabled
    if (DEBUG_OPTIONS.saveToFile) {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const errorFile = `${DEBUG_OPTIONS.outputPath}/error_${timestamp}.json`;
      fs.writeFileSync(errorFile, JSON.stringify({
        error: {
          message: error.message,
          stack: error.stack,
          name: error.name
        }
      }, null, 2));
      console.log(`Error details saved to: ${errorFile}`);
    }

    process.exit(1);
  }
}

// Run everything
main();