import { VibeKit } from '@vibe-kit/sdk';
import { createE2BProvider } from '@vibe-kit/e2b';
import { config } from 'dotenv';

// Load environment variables
config();

async function simpleGitDemo() {
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

  try {
    console.log('🚀 Starting Git Demo...');

    // Step 1: Basic setup and file creation
    console.log('Step 1: Creating files without Git...');
    const response1 = await vibekit.generateCode({
      prompt: 'Create a simple Python hello world function in a file called hello.py. Also create a README.md file explaining what this project does.',
      mode: 'code'
    });
    console.log('✅ Files created');

    // Step 2: Just list files to see what we have
    console.log('Step 2: Checking created files...');
    const response2 = await vibekit.generateCode({
      prompt: 'List all files in the current directory and show me their contents',
      mode: 'ask'
    });
    console.log('✅ Files listed');

    // For now, let's skip the Git/PR part and just see if file creation works
    console.log('🎉 Demo completed successfully!');
    console.log('Files should be created in the sandbox');

  } catch (error) {
    console.error('❌ Error in demo:', (error as Error).message);
  } finally {
    // Clean up
    try {
      await vibekit.kill();
      console.log('✅ Sandbox terminated');
    } catch (killError) {
      console.error('❌ Error killing sandbox:', (killError as Error).message);
    }
  }
}

simpleGitDemo(); 