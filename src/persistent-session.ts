import { VibeKit } from '@vibe-kit/sdk';
import { createE2BProvider } from '@vibe-kit/e2b';
import { config } from 'dotenv';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';

// Load environment variables
config();

async function createPersistentSession() {
  try {
    // Create E2B sandbox provider
    const e2bProvider = createE2BProvider({
      apiKey: process.env.E2B_API_KEY!,
      templateId: 'vibekit-claude',
    });

    // Initialize VibeKit
    const vibekit = new VibeKit()
      .withAgent({
        type: 'claude',
        provider: 'anthropic',
        apiKey: process.env.ANTHROPIC_API_KEY!,
        model: 'claude-sonnet-4-20250514',
      })
      .withSandbox(e2bProvider)
      .withGithub({
        token: process.env.GITHUB_TOKEN!,
        repository: "omeeeeeeee/test-vibekit",
      });

    console.log('🚀 Creating persistent session...');

    // Step 1: Create the Python Hello World function
    const response1 = await vibekit.generateCode({
      prompt: 'Create a simple Hello World function in Python and save it to hello.py',
      mode: 'code'
    });

    console.log('✅ Step 1 - Created Python file:');
    console.log('Result:', response1.stdout?.split('\n').pop() || 'No result');

    // Step 2: List files to confirm creation
    const response2 = await vibekit.generateCode({
      prompt: 'List all files in the current directory and show me the contents of hello.py',
      mode: 'ask'
    });

    console.log('✅ Step 2 - File listing:');
    console.log('Result:', response2.stdout?.split('\n').pop() || 'No result');

    // Step 3: Create a GitHub commit and push
    const response3 = await vibekit.generateCode({
      prompt: 'Create a git repository, add hello.py, commit with message "Add Hello World Python function", and push to GitHub',
      mode: 'code'
    });

    console.log('✅ Step 3 - GitHub push:');
    console.log('Result:', response3.stdout?.split('\n').pop() || 'No result');

    // Get sandbox ID for future sessions
    console.log('\n📋 Session Info:');
    console.log('Sandbox ID:', response1.sandboxId);
    console.log('You can resume this session later using the sandbox ID');

  } catch (error) {
    console.error('❌ Error in persistent session:', error);
  }
}

createPersistentSession(); 