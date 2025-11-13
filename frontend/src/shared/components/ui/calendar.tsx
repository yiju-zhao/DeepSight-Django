import * as React from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/shared/utils/utils"

export interface CalendarEvent {
  id: string | number
  date: Date
  title: string
  color?: string
}

export interface CalendarProps {
  events?: CalendarEvent[]
  onDateClick?: (date: Date) => void
  onEventClick?: (event: CalendarEvent) => void
  className?: string
}

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
]

export function Calendar({ events = [], onDateClick, onEventClick, className }: CalendarProps) {
  const [currentDate, setCurrentDate] = React.useState(new Date())

  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()

  // Get first day of month and total days
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  // Generate calendar grid
  const calendarDays: (number | null)[] = []

  // Add empty cells for days before month starts
  for (let i = 0; i < firstDay; i++) {
    calendarDays.push(null)
  }

  // Add days of the month
  for (let day = 1; day <= daysInMonth; day++) {
    calendarDays.push(day)
  }

  // Get events for a specific date
  const getEventsForDate = (day: number) => {
    const targetDate = new Date(year, month, day)
    return events.filter(event => {
      const eventDate = new Date(event.date)
      return eventDate.getDate() === day &&
             eventDate.getMonth() === month &&
             eventDate.getFullYear() === year
    })
  }

  // Check if date is today
  const isToday = (day: number) => {
    const today = new Date()
    return day === today.getDate() &&
           month === today.getMonth() &&
           year === today.getFullYear()
  }

  // Navigate months
  const previousMonth = () => {
    setCurrentDate(new Date(year, month - 1))
  }

  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1))
  }

  const goToToday = () => {
    setCurrentDate(new Date())
  }

  return (
    <div className={cn("w-full bg-white rounded-lg", className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-[#E3E3E3]">
        <h2 className="text-xl font-bold text-[#1E1E1E]">
          {MONTHS[month]} {year}
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={goToToday}
            className="px-3 py-1.5 text-sm font-medium text-black border border-black/30 rounded-md hover:border-black transition-all duration-300"
          >
            Today
          </button>
          <button
            onClick={previousMonth}
            className="p-2 text-black hover:bg-black/5 rounded-md transition-all duration-300"
            aria-label="Previous month"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={nextMonth}
            className="p-2 text-black hover:bg-black/5 rounded-md transition-all duration-300"
            aria-label="Next month"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="p-6">
        {/* Day headers */}
        <div className="grid grid-cols-7 gap-2 mb-4">
          {DAYS.map(day => (
            <div
              key={day}
              className="text-center text-sm font-medium text-[#666666] py-2"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Calendar days */}
        <div className="grid grid-cols-7 gap-2">
          {calendarDays.map((day, index) => {
            if (day === null) {
              return <div key={`empty-${index}`} className="aspect-square" />
            }

            const dayEvents = getEventsForDate(day)
            const today = isToday(day)

            return (
              <div
                key={day}
                className={cn(
                  "aspect-square border rounded-lg p-2 cursor-pointer transition-all duration-300",
                  "hover:shadow-[rgba(0,0,0,0.08)_0px_4px_8px]",
                  today
                    ? "border-[#CE0E2D] bg-[#CE0E2D]/5"
                    : "border-[#E3E3E3] hover:border-black/30"
                )}
                onClick={() => onDateClick?.(new Date(year, month, day))}
              >
                <div
                  className={cn(
                    "text-sm font-medium mb-1",
                    today ? "text-[#CE0E2D]" : "text-[#1E1E1E]"
                  )}
                >
                  {day}
                </div>

                {/* Event indicators */}
                {dayEvents.length > 0 && (
                  <div className="space-y-1">
                    {dayEvents.slice(0, 2).map(event => (
                      <div
                        key={event.id}
                        className="text-xs px-1.5 py-0.5 bg-black/5 rounded text-[#1E1E1E] truncate cursor-pointer hover:bg-black/10 transition-colors duration-200"
                        onClick={(e) => {
                          e.stopPropagation()
                          onEventClick?.(event)
                        }}
                        title={event.title}
                      >
                        {event.title}
                      </div>
                    ))}
                    {dayEvents.length > 2 && (
                      <div className="text-xs text-[#666666] px-1.5">
                        +{dayEvents.length - 2} more
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
