import React, { useState } from 'react';
import { Filter, X } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/shared/components/ui/select';
import { cn } from '@/shared/utils/utils';

interface SearchFiltersProps {
    venues: string[];
    years: number[];
    selectedVenue: string;
    setSelectedVenue: (value: string) => void;
    selectedYear: number | undefined;
    setSelectedYear: (value: number | undefined) => void;
    isLoading: boolean;
    topk: number;
    setTopk: (value: number) => void;
    className?: string;
}

export function SearchFilters({
    venues,
    years,
    selectedVenue,
    setSelectedVenue,
    selectedYear,
    setSelectedYear,
    isLoading,
    topk,
    setTopk,
    className
}: SearchFiltersProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    const hasActiveFilters = selectedVenue || selectedYear;

    return (
        <div className={cn("flex items-center gap-2", className)}>
            {/* Filter Icon Button */}
            <Button
                variant={isExpanded || hasActiveFilters ? "default" : "outline"}
                size="icon"
                onClick={() => setIsExpanded(!isExpanded)}
                className={cn(
                    "rounded-full transition-all duration-200",
                    (isExpanded || hasActiveFilters) ? "bg-black text-white hover:bg-gray-800" : "text-gray-500"
                )}
                title="Toggle Filters"
            >
                <Filter className="w-4 h-4" />
            </Button>

            {/* Expanded Filters */}
            {(isExpanded || hasActiveFilters) && (
                <div className="flex items-center gap-2 animate-in fade-in slide-in-from-left-2 duration-200">
                    {/* Conference Filter */}
                    <Select
                        value={selectedVenue || "ALL"}
                        onValueChange={(value) => setSelectedVenue(value === "ALL" ? "" : value)}
                        disabled={isLoading}
                    >
                        <SelectTrigger className="w-[180px] rounded-full bg-white border-gray-200">
                            <SelectValue placeholder="Conference" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">All Conferences</SelectItem>
                            {venues.map(venue => (
                                <SelectItem key={venue} value={venue}>{venue}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    {/* Year Filter */}
                    <Select
                        value={selectedYear ? selectedYear.toString() : "ALL"}
                        onValueChange={(value) => setSelectedYear(value === "ALL" ? undefined : Number(value))}
                        disabled={isLoading}
                    >
                        <SelectTrigger className="w-[120px] rounded-full bg-white border-gray-200">
                            <SelectValue placeholder="Year" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">All Years</SelectItem>
                            {years.map(year => (
                                <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    {/* Top-k Selector */}
                    <Select
                        value={topk.toString()}
                        onValueChange={(value) => setTopk(Number(value))}
                        disabled={isLoading}
                    >
                        <SelectTrigger className="w-[110px] rounded-full bg-white border-gray-200">
                            <span className="mr-1">Top</span>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {[5, 10, 20, 30, 50, 100].map(value => (
                                <SelectItem key={value} value={value.toString()}>
                                    {value}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    {/* Clear Filters Button */}
                    {hasActiveFilters && (
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => {
                                setSelectedVenue('');
                                setSelectedYear(undefined);
                            }}
                            className="rounded-full h-8 w-8 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                            title="Clear all filters"
                        >
                            <X className="w-4 h-4" />
                        </Button>
                    )}
                </div>
            )}
        </div>
    );
}
