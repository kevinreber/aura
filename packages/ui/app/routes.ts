import { index, type RouteConfig, route } from '@react-router/dev/routes';

export default [
  index('routes/home.tsx'),

  // API Routes (v1)
  route('api/v1/chat', 'routes/api.v1.chat.ts'),
  route('api/v1/health', 'routes/api.v1.health.ts'),
  route('api', 'routes/api._index.ts'),
] satisfies RouteConfig;
