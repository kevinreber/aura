import { useState, useEffect } from 'react';

interface ClockProps {
  userName: string;
  className?: string;
}

const Clock = ({ userName, className = '' }: ClockProps) => {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    // Update time every second
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getGreeting = () => {
    const hour = currentTime.getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <div className={`text-right ${className}`}>
      <div className="text-sm sm:text-base font-medium text-gray-900 dark:text-white">
        {formatTime(currentTime)}
      </div>
      <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
        {formatDate(currentTime)}
      </div>
      {/* Greeting for mobile (can be used if needed) */}
      <div className="hidden">
        {getGreeting()}, {userName}!
      </div>
    </div>
  );
};

export default Clock;
