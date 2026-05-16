import Dashboard from '../components/Dashboard';
import { ServerAIAgentAPI } from '../lib/api';
import { requireUser } from '../lib/auth.server';
import type { Route } from './+types/home';

export function meta({}: Route.MetaArgs) {
  return [
    { title: 'Daily Agent' },
    {
      name: 'description',
      content: 'Your personalized daily AI agent',
    },
  ];
}

export async function loader({ request }: Route.LoaderArgs) {
  const user = await requireUser(request);
  const displayName = user.name?.split(' ')[0] || user.email;
  console.log(`🔄 Server-side loader: Fetching dashboard data for ${user.email}...`);

  // Per-request client that attests the authenticated user to the Agent.
  const apiClient = new ServerAIAgentAPI(user.email);

  try {
    // Fetch all dashboard data on the server-side (no CORS issues!)
    const [weatherData, financialData, calendarData, todoData, commuteData] =
      await Promise.allSettled([
        apiClient.getWeather('San Francisco'),
        apiClient.getFinancialData(['MSFT', 'BTC', 'ETH', 'NVDA']),
        apiClient.getCalendar(),
        apiClient.getTodos(),
        apiClient.getCommuteOptions('to_work'), // Add commute data
      ]);

    console.log('✅ Server-side loader: Dashboard data fetched successfully');

    return {
      userName: displayName,
      userEmail: user.email,
      userPicture: user.picture,
      lastUpdated: new Date().toISOString(),
      // Extract data from Promise.allSettled results
      weather: weatherData.status === 'fulfilled' ? weatherData.value : null,
      financial: financialData.status === 'fulfilled' ? financialData.value : null,
      calendar: calendarData.status === 'fulfilled' ? calendarData.value : null,
      todos: todoData.status === 'fulfilled' ? todoData.value : null,
      commute: commuteData.status === 'fulfilled' ? commuteData.value : null,
      // Track which requests failed
      errors: {
        weather: weatherData.status === 'rejected' ? weatherData.reason?.message : null,
        financial: financialData.status === 'rejected' ? financialData.reason?.message : null,
        calendar: calendarData.status === 'rejected' ? calendarData.reason?.message : null,
        todos: todoData.status === 'rejected' ? todoData.reason?.message : null,
        commute: commuteData.status === 'rejected' ? commuteData.reason?.message : null,
      },
    };
  } catch (error) {
    console.error('❌ Server-side loader error:', error);

    // Return default data if server-side fetch fails
    return {
      userName: displayName,
      userEmail: user.email,
      userPicture: user.picture,
      lastUpdated: new Date().toISOString(),
      weather: null,
      financial: null,
      calendar: null,
      todos: null,
      commute: null,
      errors: {
        weather: 'Server-side fetch failed',
        financial: 'Server-side fetch failed',
        calendar: 'Server-side fetch failed',
        todos: 'Server-side fetch failed',
        commute: 'Server-side fetch failed',
      },
    };
  }
}

export default function Home({ loaderData }: Route.ComponentProps) {
  return (
    <Dashboard
      userName={loaderData.userName}
      userEmail={loaderData.userEmail}
      userPicture={loaderData.userPicture}
      initialWeather={loaderData.weather}
      initialFinancial={loaderData.financial}
      initialCalendar={loaderData.calendar}
      initialTodos={loaderData.todos}
      initialCommute={loaderData.commute}
      serverErrors={loaderData.errors}
    />
  );
}
