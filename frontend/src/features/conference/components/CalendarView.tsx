import React, { useState, useMemo } from 'react';
import { Calendar, CalendarEvent } from '@/shared/components/ui/calendar';
import { useInstances } from '../hooks/useConference';
import { Instance } from '../types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/shared/components/ui/dialog';
import { Calendar as CalendarIcon, MapPin, Globe, ExternalLink } from 'lucide-react';
import { format, parseISO, isWithinInterval } from 'date-fns';

interface ConferenceEventCardProps {
  instance: Instance;
  onClose: () => void;
}

const ConferenceEventCard: React.FC<ConferenceEventCardProps> = ({ instance, onClose }) => {
  const startDate = parseISO(instance.start_date);
  const endDate = parseISO(instance.end_date);

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl bg-white rounded-lg">
        <DialogHeader className="space-y-3 pb-4 border-b border-[#E3E3E3]">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <DialogTitle className="text-2xl font-bold text-[#1E1E1E] mb-2">
                {instance.venue.name} {instance.year}
              </DialogTitle>
              <DialogDescription className="text-sm text-[#666666]">
                {instance.venue.type} Conference
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-6 pt-4">
          {/* Date & Time */}
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-black/5">
              <CalendarIcon className="w-5 h-5 text-[#1E1E1E]" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-[#1E1E1E] mb-1">Date</div>
              <div className="text-sm text-[#666666]">
                {format(startDate, 'MMMM d, yyyy')} - {format(endDate, 'MMMM d, yyyy')}
              </div>
              <div className="text-xs text-[#666666] mt-1">
                {format(startDate, 'EEEE')} to {format(endDate, 'EEEE')}
              </div>
            </div>
          </div>

          {/* Location */}
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-black/5">
              <MapPin className="w-5 h-5 text-[#1E1E1E]" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-[#1E1E1E] mb-1">Location</div>
              <div className="text-sm text-[#666666]">{instance.location}</div>
            </div>
          </div>

          {/* Website */}
          {instance.website && (
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-black/5">
                <Globe className="w-5 h-5 text-[#1E1E1E]" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-[#1E1E1E] mb-1">Website</div>
                <a
                  href={instance.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-black hover:opacity-70 transition-opacity duration-300 flex items-center gap-1 group"
                >
                  <span className="underline">{instance.website}</span>
                  <ExternalLink className="w-3 h-3 opacity-60 group-hover:opacity-100" />
                </a>
              </div>
            </div>
          )}

          {/* Summary/Overview */}
          {instance.summary && (
            <div className="pt-4 border-t border-[#E3E3E3]">
              <div className="text-sm font-medium text-[#1E1E1E] mb-2">Overview</div>
              <div className="text-sm text-[#666666] leading-relaxed">
                {instance.summary}
              </div>
            </div>
          )}

          {/* Description */}
          {instance.venue.description && (
            <div className="pt-4 border-t border-[#E3E3E3]">
              <div className="text-sm font-medium text-[#1E1E1E] mb-2">About {instance.venue.name}</div>
              <div className="text-sm text-[#666666] leading-relaxed">
                {instance.venue.description}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="pt-4 border-t border-[#E3E3E3] flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-black border border-black/30 rounded-md hover:border-black transition-all duration-300"
            >
              Close
            </button>
            {instance.website && (
              <a
                href={instance.website}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 text-sm font-medium text-white bg-black rounded-md hover:opacity-80 transition-opacity duration-300 flex items-center gap-2"
              >
                Visit Website
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export const CalendarView: React.FC = () => {
  const { data: instances, isLoading, error } = useInstances();
  const [selectedInstance, setSelectedInstance] = useState<Instance | null>(null);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // Transform instances to calendar events
  const events: CalendarEvent[] = useMemo(() => {
    if (!instances) return [];

    return instances.flatMap(instance => {
      try {
        const startDate = parseISO(instance.start_date);
        const endDate = parseISO(instance.end_date);

        // Create events for each day in the date range
        const dayEvents: CalendarEvent[] = [];
        const currentDate = new Date(startDate);

        while (currentDate <= endDate) {
          dayEvents.push({
            id: `${instance.instance_id}-${currentDate.toISOString()}`,
            date: new Date(currentDate),
            title: `${instance.venue.name} ${instance.year}`,
            color: '#CE0E2D', // HUAWEI red
          });
          currentDate.setDate(currentDate.getDate() + 1);
        }

        return dayEvents;
      } catch (err) {
        console.error('Error parsing date for instance:', instance, err);
        return [];
      }
    });
  }, [instances]);

  // Find instances for a specific date
  const getInstancesForDate = (date: Date) => {
    if (!instances) return [];

    return instances.filter(instance => {
      try {
        const startDate = parseISO(instance.start_date);
        const endDate = parseISO(instance.end_date);
        return isWithinInterval(date, { start: startDate, end: endDate });
      } catch {
        return false;
      }
    });
  };

  const handleDateClick = (date: Date) => {
    const instancesOnDate = getInstancesForDate(date);
    if (instancesOnDate.length > 0) {
      setSelectedInstance(instancesOnDate[0]);
      setSelectedDate(date);
    }
  };

  const handleEventClick = (event: CalendarEvent) => {
    if (!instances) return;

    // Extract instance_id from event id (format: "instanceId-date")
    const instanceId = event.id.toString().split('-')[0];
    const instance = instances.find(i => i.instance_id.toString() === instanceId);

    if (instance) {
      setSelectedInstance(instance);
    }
  };

  const handleCloseDetails = () => {
    setSelectedInstance(null);
    setSelectedDate(null);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-black border-r-transparent mb-4"></div>
          <p className="text-sm text-[#666666]">Loading conferences...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <div className="text-center">
          <p className="text-sm text-[#CE0E2D] mb-2">Error loading conferences</p>
          <p className="text-xs text-[#666666]">
            {error instanceof Error ? error.message : 'Unknown error occurred'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#1E1E1E]">Conference Calendar</h2>
          <p className="text-sm text-[#666666] mt-1">
            View upcoming and past conferences in calendar format
          </p>
        </div>
        <div className="text-sm text-[#666666]">
          {instances?.length || 0} conferences
        </div>
      </div>

      {/* Calendar */}
      <Calendar
        events={events}
        onDateClick={handleDateClick}
        onEventClick={handleEventClick}
        className="shadow-[rgba(0,0,0,0.08)_0px_8px_12px]"
      />

      {/* Legend */}
      <div className="flex items-center gap-6 p-4 bg-white rounded-lg border border-[#E3E3E3]">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#CE0E2D]/10 border-2 border-[#CE0E2D]"></div>
          <span className="text-sm text-[#666666]">Conference Day</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#CE0E2D]"></div>
          <span className="text-sm text-[#666666]">Today</span>
        </div>
      </div>

      {/* Event Details Dialog */}
      {selectedInstance && (
        <ConferenceEventCard
          instance={selectedInstance}
          onClose={handleCloseDetails}
        />
      )}
    </div>
  );
};
