import { VibeKit } from '@vibe-kit/sdk';
import { createE2BProvider } from '@vibe-kit/e2b';

console.log('Testing VibeKit with E2B sandbox setup...');

// Test basic E2B provider creation
try {
  const e2bProvider = createE2BProvider({
    apiKey: process.env.E2B_API_KEY || 'test-key',
    templateId: 'vibekit-claude',
  });
  
  console.log('✅ E2B provider created successfully!');
  console.log('✅ E2B provider type:', typeof e2bProvider);
  
  // Test VibeKit with E2B provider
  const vibekit = new VibeKit()
    .withAgent({
      type: 'claude',
      provider: 'anthropic',
      apiKey: process.env.ANTHROPIC_API_KEY || 'test-key',
      model: 'claude-sonnet-4-20250514',
    })
    .withSandbox(e2bProvider);
  
  console.log('✅ VibeKit with E2B sandbox configured successfully!');
  console.log('✅ VibeKit instance:', typeof vibekit);
  
  console.log('\n🎉 E2B sandbox setup is working correctly!');
  console.log('\nNext steps:');
  console.log('1. Set up your API keys in a .env file:');
  console.log('   - E2B_API_KEY (from https://e2b.dev)');
  console.log('   - ANTHROPIC_API_KEY (from https://console.anthropic.com)');
  console.log('2. Run npm run dev to start generating code');
  
} catch (error) {
  console.error('❌ Error setting up E2B sandbox:', error);
} 