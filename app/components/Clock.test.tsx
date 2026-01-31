import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Clock from './Clock';

describe('Clock', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders time and date', () => {
    vi.setSystemTime(new Date('2024-06-15T14:30:00'));

    render(<Clock userName="Test User" />);

    // Check time is displayed (format may vary by locale)
    expect(screen.getByText(/02:30:00/i)).toBeInTheDocument();
    // Check date is displayed
    expect(screen.getByText(/saturday/i)).toBeInTheDocument();
    expect(screen.getByText(/june/i)).toBeInTheDocument();
  });

  it('updates time every second', () => {
    vi.setSystemTime(new Date('2024-06-15T14:30:00'));

    render(<Clock userName="Test User" />);

    // Initial time (12-hour format)
    expect(screen.getByText(/02:30:00/i)).toBeInTheDocument();

    // Advance timers to trigger the interval (time advances automatically)
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    // Time should update - it won't be :00 anymore
    expect(screen.queryByText(/02:30:00/i)).not.toBeInTheDocument();
    // Should show updated time (around :02)
    expect(screen.getByText(/02:30:0[12]/i)).toBeInTheDocument();
  });

  it('displays greeting based on time of day', () => {
    // Morning
    vi.setSystemTime(new Date('2024-06-15T09:00:00'));
    const { unmount } = render(<Clock userName="Test User" />);
    expect(screen.getByText(/good morning/i)).toBeInTheDocument();
    unmount();

    // Afternoon
    vi.setSystemTime(new Date('2024-06-15T14:00:00'));
    const { unmount: unmount2 } = render(<Clock userName="Test User" />);
    expect(screen.getByText(/good afternoon/i)).toBeInTheDocument();
    unmount2();

    // Evening
    vi.setSystemTime(new Date('2024-06-15T20:00:00'));
    render(<Clock userName="Test User" />);
    expect(screen.getByText(/good evening/i)).toBeInTheDocument();
  });

  it('includes user name in greeting', () => {
    vi.setSystemTime(new Date('2024-06-15T09:00:00'));

    render(<Clock userName="John" />);

    expect(screen.getByText(/john/i)).toBeInTheDocument();
  });

  it('applies custom className', () => {
    vi.setSystemTime(new Date('2024-06-15T14:30:00'));

    const { container } = render(<Clock userName="Test" className="custom-class" />);

    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('cleans up interval on unmount', () => {
    vi.setSystemTime(new Date('2024-06-15T14:30:00'));
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval');

    const { unmount } = render(<Clock userName="Test" />);
    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});
