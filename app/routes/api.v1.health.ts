export async function loader() {
  return new Response(
    JSON.stringify({
      status: 'ok',
      version: 'v1',
      timestamp: new Date().toISOString(),
      service: 'daily-agent-ui-api',
      endpoints: {
        'POST /api/v1/chat': 'Chat with AI assistant',
        'GET /api/v1/health': 'Health check',
      },
    }),
    {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'API-Version': 'v1',
      },
    }
  );
}
