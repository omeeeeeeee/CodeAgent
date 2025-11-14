import { VibeKit } from '@vibe-kit/vibekit';
import { createE2BProvider } from '@vibe-kit/e2b';
import { config } from 'dotenv';
import * as fs from 'fs';

// Load environment variables from .env file
config();

// Parse command line arguments
const args = process.argv.slice(2);
const promptFilePath = args[args.indexOf('--prompt-file') + 1];

// Read prompt from file
const promptData = JSON.parse(fs.readFileSync(promptFilePath, 'utf-8'));
const prompt = promptData.prompt;
// Control whether to open a PR (used by offline prompt optimization)
const NO_PR = (process.env.NO_PR || '').toLowerCase() === '1' || (process.env.NO_PR || '').toLowerCase() === 'true';
const githubRepoUrl = process.env.TARGET_GITHUB_REPO!;
// Detect if GitHub integration is enabled (explicit flag or presence of creds)
const GITHUB_ENABLED = ((process.env.GITHUB_ENABLED || '').toLowerCase() === '1'
  || (process.env.GITHUB_ENABLED || '').toLowerCase() === 'true'
  || (!!process.env.GITHUB_TOKEN && !!process.env.TARGET_GITHUB_REPO));

// Create E2B sandbox provider
const e2bProvider = createE2BProvider({
  apiKey: process.env.E2B_API_KEY!,
  templateId: 'vibekit-claude',
});

// Debug 
console.log(promptFilePath,
  prompt,
  NO_PR,
  githubRepoUrl,
  process.env.E2B_API_KEY,
  process.env.ANTHROPIC_API_KEY,
  process.env.GITHUB_TOKEN,
  process.env.GITHUB_ENABLED,
  process.env.NO_PR,
);

// Initialize VibeKit with sandbox provider
const vibekit = new VibeKit()
  .withAgent({
    type: 'claude',
    provider: 'anthropic',
    apiKey: process.env.ANTHROPIC_API_KEY || 'your-anthropic-api-key-here',
    model: 'claude-sonnet-4-20250514',
  })
  .withSandbox(e2bProvider)
  .withWorkingDirectory(`/tmp/vibekit-${Date.now()}`)
  .withTelemetry({ enabled: true })
  // .withSession("inyiby662ion9qzcfqiss")
  .withGithub({
    token: process.env.GITHUB_TOKEN!, 
    repository: githubRepoUrl, 
  });

// Collect streaming artifacts
const assistantTexts: string[] = [];
const streamedWrites: Array<{ path: string; content: string }> = [];

// Set up event listeners for streaming
vibekit.on("update", (message) => {
  // Handle streaming updates
  console.log('Streaming update:', message, '\n\n');

  try {
    if (message?.type === 'assistant' && message?.message?.content && Array.isArray(message.message.content)) {
      for (const item of message.message.content as Array<any>) {
        if (item?.type === 'text' && typeof item?.text === 'string') {
          assistantTexts.push(item.text);
        }
        if (
          item?.type === 'tool_use' &&
          item?.name === 'Write' &&
          item?.input?.file_path &&
          typeof item?.input?.content === 'string'
        ) {
          streamedWrites.push({ path: String(item.input.file_path), content: String(item.input.content) });
        }
      }
    }
  } catch {
    // ignore parse errors
  }
});

// Set up error listener
vibekit.on("error", (error) => {
  // Handle streaming errors
  console.error('Streaming error:', error, '\n\n');
});

console.log('VibeKit initialized successfully!');

// Get the current session ID
const sessionId = await vibekit.getSession();

if (sessionId) {
  console.log("Current session:", sessionId);
} else {
  console.log("No active session");
}

// Generate code from a static prompt and create a PR (first time) or push to branch (subsequent times)
// This implements iterative development: PR on first success, pushToBranch for retries/iterations
async function generateFromStaticPrompt() {
  console.log('Generating code from static prompt...');

  // Use a deterministic feature branch for each run
  const runId = Date.now();
  const featureBranch = 'feature/test-improved-prompt'; //main
  //feature/test-improved-prompt (Fintor)

  // Retry generation until success (bounded by max retries)
  const maxRetries = Number.parseInt(process.env.GEN_MAX_RETRIES || '3', 10);
  const backoffMs = Number.parseInt(process.env.GEN_RETRY_BACKOFF_MS || '2000', 10);
  const noChangesMaxRetries = Number.parseInt(process.env.NO_CHANGES_MAX_RETRIES || '1', 10);

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

  let result: { exitCode: number; stdout: string; stderr: string } | undefined;

  const hasNoChangesError = (err: any) => {
    try {
      const msg = (err?.message ?? err ?? '').toString();
      return /no\s*changes\s*found/i.test(msg);
    } catch {
      return false;
    }
  };

  async function attemptGeneration(): Promise<{ exitCode: number; stdout: string; stderr: string }> {
    let attempt = 0;
    let lastErr: any = undefined;
    while (true) {
      attempt += 1;
      console.log(`Attempt ${attempt}${Number.isFinite(maxRetries) ? `/${maxRetries}` : ''} to generate code...`);
      try {
        // reset streaming buffers for a clean attempt
        assistantTexts.length = 0;
        streamedWrites.length = 0;

        const res = await vibekit.generateCode({
          prompt,
          mode: 'code',
          branch: featureBranch,
        });
        if (res.exitCode === 0) {
          console.log('Generation succeeded.');
          return res;
        }
        console.warn(`Generation returned non-zero exitCode (${res.exitCode}).`);
        lastErr = new Error(`Generation exitCode ${res.exitCode}`);
      } catch (err: any) {
        lastErr = err;
        console.warn('Generation threw an error:', err?.message || err);
      }

      // Ensure a clean sandbox before retrying to avoid git clone into non-empty dir
      try {
        console.log('Resetting sandbox before next attempt...');
        await vibekit.kill();
        
        // Force creation of a completely new sandbox by clearing the sandbox ID
        // This prevents reusing the corrupted sandbox from the previous attempt
        console.log('Forcing new sandbox creation...');
        await vibekit.setSession(null as any);
        
        // Add delay to ensure complete cleanup
        await sleep(3000);
        console.log('Ready for fresh sandbox attempt...');
      } catch (cleanupError) {
        console.warn('Sandbox cleanup warning:', cleanupError);
        // Even if cleanup fails, still force new sandbox
        await vibekit.setSession(null as any);
        await sleep(3000);
      }

      if (attempt >= maxRetries) {
        const msg = `Generation failed after ${attempt} attempt(s)`;
        console.error(msg);
        throw lastErr instanceof Error ? lastErr : new Error(msg);
      }
      console.log(`Retrying in ${backoffMs}ms...`);
      await sleep(backoffMs);
    }
  }

  // Track if this is the first successful generation (for PR creation) or subsequent ones (for pushToBranch)
  let shouldCreatePR = true;  // Should we attempt PR creation?
  let hasPRBeenCreated = false; // Has a PR been successfully created?
  let createdPR: any = null;

  // Outer retries for the "No changes found" PR scenario
  let noChangesAttempt = 0;
  while (true) {
    result = await attemptGeneration();

  // Extract any files written by the agent from streaming stdout
  const writes: Array<{ path: string; content: string }> = [...streamedWrites];
  try {
    for (const line of ((result?.stdout as string) || '').split('\n')) {
      try {
        const obj = JSON.parse(line);
        const contents = obj?.message?.content as Array<any> | undefined;
        if (obj?.type === 'assistant' && Array.isArray(contents)) {
          for (const item of contents) {
            if (
              item?.type === 'tool_use' &&
              item?.name === 'Write' &&
              item?.input?.file_path &&
              typeof item?.input?.content === 'string'
            ) {
              writes.push({ path: item.input.file_path, content: item.input.content });
            }
          }
        }
      } catch { /* ignore non-JSON lines */ }
    }
  } catch { /* ignore parse errors */ }

  // Fallback: if no writes captured, try to extract first code block from assistant text or stdout
  if (writes.length === 0) {
    // Try assistant texts first, then fallback to stdout
    let sourceText = '';
    let source = '';
    
    if (assistantTexts.length > 0) {
      sourceText = assistantTexts.join('\n\n');
      source = 'assistantTexts';
      console.log('🔍 Using assistantTexts for code extraction');
    } else if (result?.stdout) {
      sourceText = result.stdout;
      source = 'stdout';
      console.log('🔍 Using stdout for code extraction (assistantTexts empty)');
    }
    
    if (sourceText) {
      const code = extractFirstCodeBlock(sourceText);
      if (code) {
      // Save locally as fallback instead of trying GitHub operations
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const localFilename = `generated_graph_${timestamp}.py`;
      
      try {
        fs.writeFileSync(localFilename, code, 'utf-8');
        console.log(`\n🚀 FALLBACK: Code saved locally to ${localFilename}`);
        console.log(`📝 Reason: Claude generated code but didn't write to repository`);
        console.log(`📄 Source: Extracted from ${source}`);
        
        // Surface a compact, parseable result back to Python (skip GitHub operations)
        console.log('AGENT_RESPONSE_START');
        console.log(JSON.stringify({
          response: `Code saved locally to ${localFilename} (no GitHub operations)`,
          exitCode: result!.exitCode,
          error: result!.stderr,
          noPr: true, // Force no PR since we're doing local fallback
          codeWrites: [{ path: localFilename, content: code }],
          pullRequest: null,
          branchName: featureBranch,
          localFallback: true,
          localFile: localFilename
        }));
        console.log('AGENT_RESPONSE_END');
        
        return result;
      } catch (saveError) {
        console.error(`Failed to save code locally: ${saveError}`);
        // Continue with original flow if local save fails
        writes.push({ path: 'extraction_fallback', content: code });
      }
      } else {
        console.log('⚠️  No Python code found in response for local fallback');
      }
    } else {
      console.log('⚠️  No source text available for code extraction');
    }
  }

  console.log('\n\n=============RESULT=============',
    result,
    "=============RESULT=============\n\n"
  );

  // Debug: Log what files were actually written
  console.log('\n=== FILES ACTUALLY WRITTEN DEBUG ===');
  console.log('StreamedWrites array length:', streamedWrites.length);
  console.log('StreamedWrites:', JSON.stringify(streamedWrites, null, 2));
  console.log('Final writes array length:', writes.length);
  console.log('Final writes:', JSON.stringify(writes, null, 2));
  console.log('=== END FILE WRITES DEBUG ===\n');

    // Handle GitHub integration: PR on first success, pushToBranch on subsequent attempts
    let responseMsg = '';
    if (NO_PR || writes.length === 0) {
      const reason = writes.length === 0 ? 'No files written' : 'NO_PR is set';
      console.log(`${reason}. Skipping GitHub operations.`);
      responseMsg = `Generated changes on ${featureBranch} (GitHub operations skipped - ${reason})`;
    } else {
      try {
        if (shouldCreatePR && !hasPRBeenCreated) {
          console.log('Creating pull request...');
          createdPR = await vibekit.createPullRequest();
          responseMsg = `PR created: ${createdPR.html_url} (PR #${createdPR.number})`;
          hasPRBeenCreated = true;
          shouldCreatePR = false; // Don't try to create PR again
        } else {
          console.log('Pushing updates to existing branch...');
          // Type assertion needed as pushToBranch is not exposed in VibeKit interface
          await (vibekit as any).agent.pushToBranch(featureBranch);
          responseMsg = `Updated existing PR branch: ${featureBranch}${createdPR ? ` (PR #${createdPR.number})` : ''}`;
        }
      } catch (err: any) {
        if (hasNoChangesError(err) && noChangesAttempt < noChangesMaxRetries) {
          noChangesAttempt += 1;
          console.warn(`GitHub operation failed with 'No changes found'. Re-generating (attempt ${noChangesAttempt}/${noChangesMaxRetries})...`);
          // After first failed attempt, switch to pushToBranch for subsequent tries
          shouldCreatePR = false;
          // loop back to re-generate and try again
          continue;
        }
        // For non-"no changes" errors on PR creation, fall back to pushToBranch on next try
        if (shouldCreatePR && !hasPRBeenCreated) {
          console.warn(`PR creation failed: ${err.message}. Will use pushToBranch on retry.`);
          shouldCreatePR = false;
          // Retry once with pushToBranch instead of failing completely
          if (noChangesAttempt < noChangesMaxRetries) {
            noChangesAttempt += 1;
            continue;
          }
        }
        throw err;
      }
    }

  // Surface a compact, parseable result back to Python
    console.log('AGENT_RESPONSE_START');
    console.log(JSON.stringify({
      response: responseMsg,
      exitCode: result!.exitCode,
      error: result!.stderr,
      noPr: NO_PR,
      codeWrites: writes,
      pullRequest: createdPR ? {
        number: createdPR.number,
        html_url: createdPR.html_url,
        branchName: createdPR.branchName
      } : null,
      branchName: featureBranch,
    }));
    console.log('AGENT_RESPONSE_END');

    // Always try to kill the sandbox at the end of a run to avoid residual state
    try {
      await vibekit.kill();
      console.log('Sandbox terminated successfully');
    } catch {
      // ignore cleanup errors
    }

    return result;
  }
}

// Run the example
generateFromStaticPrompt()
  .catch(error => {
    // Log errors in the same debug-friendly format
    console.log('AGENT_RESPONSE_START');
    console.log(JSON.stringify({
      error: {
        message: error.message,
        stack: error.stack,
        name: error.name
      },
      exitCode: 1,
      stdout: '',
      stderr: error.message,
      parsedStdout: []
    }, null, 2));
    console.log('AGENT_RESPONSE_END');
    process.exit(1);
  });

// TODO: Uncomment out later
// // Kill the sandbox when done
// await vibekit.kill();
// console.log("Sandbox terminated successfully");

// Helpers
function extractFirstCodeBlock(text: string): string | null {
  if (!text) return null;
  // Match triple backtick blocks, prefer python if present
  const regex = /```(\w+)?\n([\s\S]*?)```/g;
  let match: RegExpExecArray | null = null;
  let first: { lang: string | undefined; code: string } | null = null;
  let python: { lang: string | undefined; code: string } | null = null;
  while ((match = regex.exec(text)) !== null) {
    const lang = match[1]?.toLowerCase();
    const code = match[2] || '';
    if (!first) first = { lang, code };
    if (lang === 'py' || lang === 'python') {
      python = { lang, code };
      break;
    }
  }
  const chosen = python || first;
  return chosen ? chosen.code.trim() : null;
}