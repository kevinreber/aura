import React, { useEffect, useState } from 'react';
import type {
  BasicCommuteData,
  CommuteOptionsData,
  ShuttleScheduleData,
} from '../lib/api';

interface CommuteDashboardProps {
  className?: string;
}

export function CommuteDashboard({ className }: CommuteDashboardProps) {
  const [commuteData, setCommuteData] = useState<CommuteOptionsData | null>(null);
  const [shuttleData, setShuttleData] = useState<ShuttleScheduleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDirection, setSelectedDirection] = useState<'to_work' | 'from_work'>('to_work');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    fetchCommuteData();
  }, [selectedDirection, refreshKey]);

  const fetchCommuteData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Go through the UI proxy so the session cookie carries auth — the
      // browser can't attach INTERNAL_AUTH_SECRET directly.
      const commuteResp = await fetch('/api/v1/commute-options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          direction: selectedDirection,
          include_driving: true,
          include_transit: true,
        }),
      });
      if (!commuteResp.ok) throw new Error(`commute-options ${commuteResp.status}`);
      setCommuteData((await commuteResp.json()) as CommuteOptionsData);

      // Fetch shuttle schedule (MV Caltrain to LinkedIn for morning, reverse for evening)
      const shuttleOrigin =
        selectedDirection === 'to_work' ? 'mountain_view_caltrain' : 'linkedin_transit_center';
      const shuttleDestination =
        selectedDirection === 'to_work' ? 'linkedin_transit_center' : 'mountain_view_caltrain';

      const shuttleResp = await fetch('/api/v1/shuttle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ origin: shuttleOrigin, destination: shuttleDestination }),
      });
      if (!shuttleResp.ok) throw new Error(`shuttle ${shuttleResp.status}`);
      setShuttleData((await shuttleResp.json()) as ShuttleScheduleData);
    } catch (err) {
      setError('Failed to load commute data');
      console.error('Error fetching commute data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  const getTrafficStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'light traffic':
        return 'text-green-600 dark:text-green-400';
      case 'moderate traffic':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'heavy traffic':
      case 'very heavy traffic':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getTrafficStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'light traffic':
        return '🟢';
      case 'moderate traffic':
        return '🟡';
      case 'heavy traffic':
      case 'very heavy traffic':
        return '🔴';
      default:
        return '⚪';
    }
  };

  if (loading) {
    return (
      <div
        className={`rounded-2xl border border-slate-200/70 bg-white/80 shadow-sm shadow-slate-200/40 backdrop-blur-sm transition-all dark:border-white/10 dark:bg-white/[0.04] dark:shadow-none p-4 sm:p-6 ${className || ''}`}
      >
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`rounded-2xl border border-slate-200/70 bg-white/80 shadow-sm shadow-slate-200/40 backdrop-blur-sm transition-all dark:border-white/10 dark:bg-white/[0.04] dark:shadow-none p-4 sm:p-6 ${className || ''}`}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">🚗 Commute</h3>
          <button
            onClick={handleRefresh}
            className="px-3 py-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
          >
            Retry
          </button>
        </div>
        <div className="text-red-600 dark:text-red-400 text-sm">{error}</div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-2xl border border-slate-200/70 bg-white/80 shadow-sm shadow-slate-200/40 backdrop-blur-sm transition-all dark:border-white/10 dark:bg-white/[0.04] dark:shadow-none p-4 sm:p-6 ${className || ''}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">🚗 Commute</h3>
        <div className="flex items-center gap-4">
          {/* Direction Toggle */}
          <select
            value={selectedDirection}
            onChange={(e) => setSelectedDirection(e.target.value as 'to_work' | 'from_work')}
            className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
          >
            <option value="to_work">To Work</option>
            <option value="from_work">From Work</option>
          </select>

          <button
            onClick={handleRefresh}
            className="px-3 py-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* AI Recommendation */}
      {commuteData?.data.recommendation && (
        <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700/50 rounded-lg">
          <div className="flex items-start gap-2">
            <span className="text-blue-600 dark:text-blue-400">💡</span>
            <div>
              <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-1">Recommendation</h4>
              <p className="text-sm text-blue-800 dark:text-blue-200">
                {commuteData.data.recommendation}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {/* Driving Option */}
        {commuteData?.data.driving && (
          <div className="border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-700/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xl">🚗</span>
              <h4 className="font-semibold text-gray-900 dark:text-white">Driving</h4>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Duration:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {commuteData.data.driving.duration_minutes} min
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Distance:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {commuteData.data.driving.distance_miles} mi
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Est. Fuel:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {commuteData.data.driving.estimated_fuel_gallons} gal
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Route:</span>
                <span className="font-medium text-xs text-gray-900 dark:text-white">
                  {commuteData.data.driving.route_summary}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Traffic:</span>
                <div className="flex items-center gap-1">
                  <span>{getTrafficStatusIcon(commuteData.data.driving.traffic_status)}</span>
                  <span
                    className={`font-medium ${getTrafficStatusColor(commuteData.data.driving.traffic_status)}`}
                  >
                    {commuteData.data.driving.traffic_status}
                  </span>
                </div>
              </div>

              <div className="pt-2 border-t border-gray-100 dark:border-gray-600">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Depart:</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {commuteData.data.driving.departure_time}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Arrive:</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {commuteData.data.driving.arrival_time}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Transit Option */}
        {commuteData?.data.transit && (
          <div className="border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-700/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xl">🚆</span>
              <div>
                <h4 className="font-semibold text-gray-900 dark:text-white">Transit</h4>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {selectedDirection === 'to_work'
                    ? 'South San Francisco → Mountain View'
                    : 'Mountain View → South San Francisco'}
                </p>
              </div>
            </div>

            <div className="space-y-2 text-sm mb-4">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Total Time:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {commuteData.data.transit.total_duration_minutes} min
                </span>
              </div>

              <div className="text-xs space-y-1">
                <div className="flex justify-between text-gray-500 dark:text-gray-400">
                  <span>
                    • Caltrain {selectedDirection === 'to_work' ? '(S.SF → MV)' : '(MV → S.SF)'}:
                  </span>
                  <span>{commuteData.data.transit.caltrain_duration_minutes} min</span>
                </div>
                <div className="flex justify-between text-gray-500 dark:text-gray-400">
                  <span>
                    • MV Connector{' '}
                    {selectedDirection === 'to_work'
                      ? '(MV Caltrain → LinkedIn)'
                      : '(LinkedIn → MV Caltrain)'}
                    :
                  </span>
                  <span>{commuteData.data.transit.shuttle_duration_minutes} min</span>
                </div>
                <div className="flex justify-between text-gray-500 dark:text-gray-400">
                  <span>• Walking:</span>
                  <span>{commuteData.data.transit.walking_duration_minutes} min</span>
                </div>
                <div className="flex justify-between text-gray-500 dark:text-gray-400">
                  <span>• Transfer:</span>
                  <span>{commuteData.data.transit.transfer_time_minutes} min</span>
                </div>
              </div>
            </div>

            {/* Next Trains */}
            {commuteData.data.transit.next_departures.length > 0 && (
              <div className="mb-3">
                <h5 className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Next Caltrain Departures{' '}
                  {selectedDirection === 'to_work'
                    ? '(South SF → Mountain View)'
                    : '(Mountain View → South SF)'}
                  :
                </h5>
                <div className="space-y-1">
                  {commuteData.data.transit.next_departures.slice(0, 2).map((train, idx) => (
                    <div key={idx} className="flex justify-between text-xs">
                      <span className="text-gray-600 dark:text-gray-400">
                        Train {train.train_number}
                      </span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {train.departure_time} → {train.arrival_time}
                        {train.delay_minutes > 0 && (
                          <span className="text-red-500 dark:text-red-400 ml-1">
                            +{train.delay_minutes}min
                          </span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Shuttle Schedule */}
      {shuttleData && (
        <div className="mt-6 border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-700/50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">🚌</span>
            <h4 className="font-semibold text-gray-900 dark:text-white">MV Connector Shuttle</h4>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Duration:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {shuttleData.data.duration_minutes} min
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Frequency:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  Every {shuttleData.data.frequency_minutes} min
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Service Hours:</span>
                <span className="font-medium text-xs text-gray-900 dark:text-white">
                  {shuttleData.data.service_hours}
                </span>
              </div>
            </div>

            <div>
              <h5 className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                Next Departures:
              </h5>
              {shuttleData.data.next_departures.length > 0 ? (
                <div className="space-y-1">
                  {shuttleData.data.next_departures.slice(0, 3).map((shuttle, idx) => (
                    <div key={idx} className="text-xs font-medium text-gray-900 dark:text-white">
                      {shuttle.departure_time}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {new Date().getDay() === 0 || new Date().getDay() === 6
                    ? 'No service on weekends (Monday-Friday only)'
                    : 'No more departures today'}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Last Updated */}
      <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-600">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Last updated:{' '}
          {commuteData ? new Date(commuteData.timestamp).toLocaleTimeString() : 'Unknown'}
        </p>
      </div>
    </div>
  );
}
