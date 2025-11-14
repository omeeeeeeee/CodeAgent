import { VibeKit } from '@vibe-kit/sdk';

console.log('Testing VibeKit setup...');

// Test basic VibeKit initialization
try {
  const vibekit = new VibeKit();
  console.log('✅ VibeKit imported and instantiated successfully!');
  
  // Test the VibeKit instance
  console.log('✅ VibeKit instance created:', typeof vibekit);
  console.log('✅ VibeKit methods available:', Object.getOwnPropertyNames(Object.getPrototypeOf(vibekit)));
  
  console.log('\n🎉 VibeKit setup is working correctly!');
  console.log('\nNext steps:');
  console.log('1. Set up your API keys in a .env file');
  console.log('2. Configure your agent in src/index.ts');
  console.log('3. Run npm run dev to start generating code');
  
} catch (error) {
  console.error('❌ Error setting up VibeKit:', error);
} 