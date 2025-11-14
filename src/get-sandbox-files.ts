import { VibeKit } from '@vibe-kit/sdk';
import { createE2BProvider } from '@vibe-kit/e2b';
import { config } from 'dotenv';
import { writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';

// Load environment variables
config();

async function getSandboxFiles() {
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
      .withSandbox(e2bProvider);

    console.log('🔍 Retrieving files from sandbox...');

    // Get the session (sandbox) and list files
    const response = await vibekit.generateCode({
      prompt: 'List all files in the workspace directory and show me the content of hello.js',
      mode: 'ask'
    });

    console.log('📋 Sandbox Response:');
    console.log(JSON.stringify(response, null, 2));

  } catch (error) {
    console.error('❌ Error retrieving sandbox files:', error);
  }
}

getSandboxFiles(); 