import { config } from 'dotenv';

// Load environment variables
config();

console.log('🔍 Debugging API Keys...\n');

// Check if .env file is loaded
console.log('📁 Environment Variables:');
console.log('E2B_API_KEY:', process.env.E2B_API_KEY ? '✅ Set' : '❌ Not set');
console.log('ANTHROPIC_API_KEY:', process.env.ANTHROPIC_API_KEY ? '✅ Set' : '❌ Not set');

// Check API key formats
if (process.env.E2B_API_KEY) {
  const e2bKey = process.env.E2B_API_KEY;
  console.log('\n🔑 E2B API Key Analysis:');
  console.log('Length:', e2bKey.length);
  console.log('Starts with:', e2bKey.substring(0, 10) + '...');
  console.log('Contains spaces:', e2bKey.includes(' '));
  console.log('Contains quotes:', e2bKey.includes('"') || e2bKey.includes("'"));
  
  // Common issues
  if (e2bKey.includes(' ')) {
    console.log('⚠️  WARNING: API key contains spaces - this might cause issues');
  }
  if (e2bKey.includes('"') || e2bKey.includes("'")) {
    console.log('⚠️  WARNING: API key contains quotes - remove them from .env file');
  }
  if (e2bKey === 'your-e2b-api-key-here') {
    console.log('❌ ERROR: You still have the placeholder value!');
  }
}

if (process.env.ANTHROPIC_API_KEY) {
  const anthropicKey = process.env.ANTHROPIC_API_KEY;
  console.log('\n🔑 Anthropic API Key Analysis:');
  console.log('Length:', anthropicKey.length);
  console.log('Starts with:', anthropicKey.substring(0, 10) + '...');
  console.log('Contains spaces:', anthropicKey.includes(' '));
  console.log('Contains quotes:', anthropicKey.includes('"') || anthropicKey.includes("'"));
  
  if (anthropicKey === 'your-anthropic-api-key-here') {
    console.log('❌ ERROR: You still have the placeholder value!');
  }
}

console.log('\n📋 Troubleshooting Tips:');
console.log('1. Make sure your .env file is in the project root directory');
console.log('2. Remove any quotes around your API keys in .env');
console.log('3. Don\'t add spaces around the = sign in .env');
console.log('4. Make sure you copied the full API key from E2B dashboard');
console.log('5. Check that your E2B account is active and has credits');

console.log('\n📝 Example .env format:');
console.log('E2B_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx');
console.log('ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'); 