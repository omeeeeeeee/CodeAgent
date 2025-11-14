import { VibeKit } from '@vibe-kit/sdk';

// Example of how to create a custom agent configuration
export const createExampleAgent = () => {
  const vibekit = new VibeKit()
    .withAgent({
      type: 'codex',
      provider: 'openai',
      apiKey: process.env.OPENAI_API_KEY || 'your-api-key-here',
      model: 'gpt-4'
    })
    .withWorkingDirectory('./workspace')
    .withTelemetry({ enabled: true });

  return vibekit;
};

// Example function to demonstrate agent usage
export async function runExampleAgent() {
  const agent = createExampleAgent();
  
  try {
    console.log('Starting example agent...');
    
    const response = await agent.generateCode({
      prompt: 'Create a simple calculator function in JavaScript',
      mode: 'code'
    });
    
    console.log('Agent response:', response);
    return response;
  } catch (error) {
    console.error('Error running agent:', error);
    throw error;
  }
} 