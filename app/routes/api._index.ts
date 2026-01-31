export async function loader() {
  return new Response(
    JSON.stringify({
      service: 'Daily Agent UI API',
      description: 'Proxy API for the Daily Agent UI application',
      versions: {
        v1: {
          endpoints: {
            'GET /api/v1/health': 'Health check endpoint',
            'POST /api/v1/chat': 'Chat proxy to AI Agent API',
          },
          status: 'stable',
          baseUrl: '/api/v1',
        },
      },
      current_version: 'v1',
      documentation: 'https://github.com/your-org/daily-agent-ui',
      timestamp: new Date().toISOString(),
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }
  );
}
