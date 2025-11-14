import { config } from 'dotenv';

// Load environment variables
config();

async function testAnthropicKey() {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  
  if (!apiKey) {
    console.log('❌ ANTHROPIC_API_KEY not found in .env file');
    return;
  }

  console.log('🔍 Testing Anthropic API Key...');
  console.log('Key starts with:', apiKey.substring(0, 20) + '...');
  console.log('Key length:', apiKey.length);

  try {
    // Simple test request to Anthropic API
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 10,
        messages: [
          {
            role: 'user',
            content: 'Hello'
          }
        ]
      })
    });

    if (response.ok) {
      console.log('✅ Anthropic API key is valid!');
    } else {
      const error = await response.text();
      console.log('❌ Anthropic API key is invalid:', response.status, error);
    }
  } catch (error) {
    console.log('❌ Error testing Anthropic API key:', (error as Error).message);
  }
}

testAnthropicKey(); 