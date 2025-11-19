import React, { useMemo } from 'react';
import { format, parse } from 'date-fns';
import { Calendar, Clock, User, FileText, Video, Link as LinkIcon } from 'lucide-react';
import { Session } from '../types';
import { useQuery } from '@tanstack/react-query';
import { conferenceService } from '../services/ConferenceService';

interface SessionListProps {
    instanceId: number;
}

export const SessionList: React.FC<SessionListProps> = ({ instanceId }) => {
    const { data: sessions, isLoading } = useQuery({
        queryKey: ['sessions', instanceId],
        queryFn: () => conferenceService.getSessions({ instance: instanceId }),
    });

    const groupedSessions = useMemo(() => {
        if (!sessions) return {};

        // Sort sessions by date and time
        const sorted = [...sessions].sort((a, b) => {
            const dateA = new Date(`${a.date} ${a.start_time}`);
            const dateB = new Date(`${b.date} ${b.start_time}`);
            return dateA.getTime() - dateB.getTime();
        });

        // Group by date
        return sorted.reduce((acc, session) => {
            const date = session.date;
            if (!acc[date]) {
                acc[date] = [];
            }
            acc[date].push(session);
            return acc;
        }, {} as Record<string, Session[]>);
    }, [sessions]);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-black border-r-transparent mb-4"></div>
                    <p className="text-sm text-[#666666]">Loading sessions...</p>
                </div>
            </div>
        );
    }

    if (!sessions || sessions.length === 0) {
        return (
            <div className="text-center py-16 bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] border border-[#E3E3E3]">
                <Calendar className="w-16 h-16 text-[#666666] mx-auto mb-4" />
                <h3 className="text-lg font-medium text-[#1E1E1E] mb-2">
                    No sessions found
                </h3>
                <p className="text-[#666666]">
                    There are no sessions scheduled for this conference yet.
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {Object.entries(groupedSessions).map(([date, dateSessions]) => (
                <div key={date} className="space-y-4">
                    <div className="flex items-center space-x-2 sticky top-0 bg-[#F7F7F7] py-2 z-10">
                        <Calendar className="w-5 h-5 text-[#CE0E2D]" />
                        <h3 className="text-lg font-bold text-[#1E1E1E]">
                            {format(new Date(date), 'EEEE, MMMM d, yyyy')}
                        </h3>
                    </div>

                    <div className="grid gap-4">
                        {dateSessions.map((session) => (
                            <div
                                key={session.id}
                                className="bg-white rounded-lg p-6 shadow-[rgba(0,0,0,0.05)_0px_1px_2px] border border-[#E3E3E3] hover:shadow-[rgba(0,0,0,0.08)_0px_8px_12px] transition-all duration-300"
                            >
                                <div className="flex flex-col md:flex-row gap-6">
                                    {/* Time Column */}
                                    <div className="md:w-48 flex-shrink-0">
                                        <div className="flex items-center text-[#CE0E2D] font-medium mb-1">
                                            <Clock className="w-4 h-4 mr-2" />
                                            {session.start_time} - {session.end_time}
                                        </div>
                                        <div className="inline-block px-2 py-1 bg-[#F5F5F5] rounded text-xs font-medium text-[#666666] uppercase tracking-wide">
                                            {session.type}
                                        </div>
                                    </div>

                                    {/* Content Column */}
                                    <div className="flex-1 space-y-3">
                                        <h4 className="text-xl font-bold text-[#1E1E1E] leading-tight">
                                            {session.title}
                                        </h4>

                                        {session.speaker && (
                                            <div className="flex items-start text-[#444444]">
                                                <User className="w-4 h-4 mr-2 mt-1 flex-shrink-0" />
                                                <span>{session.speaker}</span>
                                            </div>
                                        )}

                                        {session.abstract && (
                                            <p className="text-[#666666] text-sm leading-relaxed line-clamp-3">
                                                {session.abstract}
                                            </p>
                                        )}

                                        <div className="flex flex-wrap gap-3 pt-2">
                                            {session.url && (
                                                <a
                                                    href={session.url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="flex items-center text-xs font-medium text-[#CE0E2D] hover:underline"
                                                >
                                                    <LinkIcon className="w-3 h-3 mr-1" />
                                                    Session Link
                                                </a>
                                            )}
                                            {session.transcript && (
                                                <span className="flex items-center text-xs font-medium text-[#666666] bg-[#F5F5F5] px-2 py-1 rounded">
                                                    <FileText className="w-3 h-3 mr-1" />
                                                    Transcript Available
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
};
