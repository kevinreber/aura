import { buildAgentAuthHeaders } from '../lib/agent-auth.server';
import { requireUserJson } from '../lib/auth.server';

export async function action({ request }: { request: Request }) {
  console.log('🤖 API v1 Chat Stream: Processing request...');

  let user;
  try {
    user = await requireUserJson(request);
  } catch (resp) {
    if (resp instanceof Response) return resp;
    throw resp;
  }

  try {
    const body = await request.json();
    const { message } = body;

    if (!message?.trim()) {
      return new Response(JSON.stringify({ error: 'Message is required' }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          'API-Version': 'v1',
        },
      });
    }

    console.log(`💬 v1 API: Streaming message from ${user.email}: ${message}`);

    // Get AI Agent API URL from environment
    const aiAgentUrl = process.env.VITE_AI_AGENT_API_URL || 'http://localhost:8001';

    // Proxy streaming request to AI Agent API (server-to-server, no CORS!)
    const response = await fetch(`${aiAgentUrl}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...buildAgentAuthHeaders(user.email),
      },
      body: JSON.stringify({ message: message.trim() }),
    });

    if (!response.ok) {
      throw new Error(`AI Agent API error: ${response.status} ${response.statusText}`);
    }

    // Stream the SSE response directly to the client
    console.log('✅ API v1 Chat Stream: Streaming response...');

    return new Response(response.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'API-Version': 'v1',
      },
    });
  } catch (error) {
    console.error('❌ API v1 Chat Stream error:', error);

    // Return error as SSE format for consistency
    const errorMessage = `data: [ERROR] Sorry, I'm having trouble connecting to the AI service right now. Please try again later.\n\n`;

    return new Response(errorMessage, {
      status: 200, // Use 200 for SSE even on error, error is in the data
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'API-Version': 'v1',
      },
    });
  }
}
