import { index, type RouteConfig, route } from '@react-router/dev/routes';

export default [
  index('routes/home.tsx'),

  // Auth
  route('login', 'routes/login.tsx'),
  route('auth/google', 'routes/auth.google.ts'),
  route('auth/google/callback', 'routes/auth.google.callback.ts'),
  route('auth/logout', 'routes/auth.logout.ts'),

  // API Routes (v1)
  route('api/v1/chat', 'routes/api.v1.chat.ts'),
  route('api/v1/chat/stream', 'routes/api.v1.chat.stream.ts'),
  route('api/v1/health', 'routes/api.v1.health.ts'),
  route('api/v1/preferences', 'routes/api.v1.preferences.ts'),
  route('api/v1/commute-options', 'routes/api.v1.commute-options.ts'),
  route('api/v1/shuttle', 'routes/api.v1.shuttle.ts'),
  route('api/v1/todos', 'routes/api.v1.todos.ts'),
  route('api/v1/financial', 'routes/api.v1.financial.ts'),
  route('api/v1/briefing/tomorrow', 'routes/api.v1.briefing.tomorrow.ts'),
  route('api/v1/suggestions/feedback', 'routes/api.v1.suggestions.feedback.ts'),
  route('api', 'routes/api._index.ts'),
] satisfies RouteConfig;
