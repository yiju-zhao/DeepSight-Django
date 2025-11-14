import React from 'react';
import { Search, Calendar as CalendarIcon, MapPin, Star, Users, FileText, X, ChevronDown, ChevronUp } from 'lucide-react';

interface Instance {
  instance_id: number;
  venue: {
    name: string;
    type: string;
  };
  year: number;
  start_date: string;
  location?: string;
}

interface GroupedConference {
  venue: {
    name: string;
    type: string;
  };
  instances: Instance[];
  yearRange: { min: number; max: number };
}

interface ConferenceSelectionDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  conferenceSearchInput: string;
  onSearchInputChange: (value: string) => void;
  popularConferences: Instance[];
  groupedConferences: Record<string, GroupedConference>;
  selectedInstance?: Instance | null;
  onInstanceSelect: (instanceId: number) => void;
  instancesLoading: boolean;
  allConferencesExpanded: boolean;
  onToggleAllConferences: () => void;
}

/**
 * Drawer component for conference selection with HUAWEI-style design
 * Slides in from right with smooth animations and overlay
 */
const ConferenceSelectionDrawer: React.FC<ConferenceSelectionDrawerProps> = ({
  isOpen,
  onClose,
  conferenceSearchInput,
  onSearchInputChange,
  popularConferences,
  groupedConferences,
  selectedInstance,
  onInstanceSelect,
  instancesLoading,
  allConferencesExpanded,
  onToggleAllConferences,
}) => {
  const handleInstanceClick = (instanceId: number) => {
    onInstanceSelect(instanceId);
    onClose(); // Close drawer after selection
  };

  return (
    <>
      {/* Overlay */}
      <div
        className={`fixed inset-0 bg-black/60 z-50 transition-opacity duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-full md:w-[600px] bg-white shadow-[rgba(0,0,0,0.16)_0px_16px_24px] z-50 transform transition-transform duration-350 ease-out overflow-y-auto ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-[#E3E3E3] z-10">
          <div className="flex items-center justify-between px-6 py-4">
            <div>
              <h2 className="text-xl font-bold text-[#1E1E1E]">Select Conference</h2>
              <p className="text-sm text-[#666666] mt-0.5">Choose a conference to explore</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-[#F5F5F5] transition-colors duration-200"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5 text-[#1E1E1E]" />
            </button>
          </div>

          {/* Search Bar */}
          <div className="px-6 pb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#666666] w-5 h-5" />
              <input
                type="text"
                placeholder="Search conferences, venues, or years..."
                value={conferenceSearchInput}
                onChange={(e) => onSearchInputChange(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-white border border-[#E3E3E3] rounded-lg text-[#1E1E1E] placeholder-[#666666] focus:outline-none focus:ring-2 focus:ring-black/10 focus:border-black transition-all duration-300"
              />
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6 space-y-6">
          {/* Selected Conference Badge */}
          {selectedInstance && (
            <div className="bg-black text-white rounded-lg p-4 shadow-[rgba(0,0,0,0.08)_0px_8px_12px]">
              <div className="text-xs font-medium text-white/70 mb-1">Currently Selected</div>
              <div className="text-base font-bold">
                {selectedInstance.venue.name} {selectedInstance.year}
              </div>
              {selectedInstance.location && (
                <div className="flex items-center text-xs text-white/70 mt-2">
                  <MapPin className="w-3 h-3 mr-1" />
                  {selectedInstance.location}
                </div>
              )}
            </div>
          )}

          {/* Recent Conferences */}
          {!conferenceSearchInput && popularConferences.length > 0 && (
            <div>
              <div className="flex items-center mb-3">
                <Star className="w-5 h-5 text-[#CE0E2D] mr-2" />
                <h3 className="text-base font-semibold text-[#1E1E1E]">Recent</h3>
              </div>
              <div className="space-y-2">
                {popularConferences.map((instance) => (
                  <button
                    key={instance.instance_id}
                    onClick={() => handleInstanceClick(instance.instance_id)}
                    className={`w-full p-4 rounded-lg border transition-all duration-300 text-left ${
                      selectedInstance?.instance_id === instance.instance_id
                        ? 'border-black bg-black/5 shadow-[rgba(0,0,0,0.08)_0px_8px_12px]'
                        : 'border-[#E3E3E3] hover:border-black/30 hover:shadow-[rgba(0,0,0,0.04)_0px_4px_8px]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-semibold text-[#1E1E1E] text-sm">
                        {instance.venue.name}
                      </div>
                      <div className="flex items-center text-xs text-[#666666]">
                        <CalendarIcon className="w-3.5 h-3.5 mr-1" />
                        {instance.year}
                      </div>
                    </div>
                    <div className="text-xs text-[#666666] mb-1">{instance.venue.type}</div>
                    {instance.location && (
                      <div className="flex items-center text-xs text-[#666666]">
                        <MapPin className="w-3 h-3 mr-1" />
                        {instance.location}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* All Conferences Grid */}
          <div>
            <button
              onClick={onToggleAllConferences}
              className="flex items-center justify-between w-full mb-4 hover:opacity-80 transition-opacity duration-300"
            >
              <div className="flex items-center">
                <Users className="w-5 h-5 text-[#1E1E1E] mr-2 opacity-80" />
                <h3 className="text-base font-semibold text-[#1E1E1E]">All Conferences</h3>
                <span className="ml-2 text-sm text-[#666666]">
                  ({Object.keys(groupedConferences).length} venues)
                </span>
              </div>
              {allConferencesExpanded ? (
                <ChevronUp className="w-5 h-5 text-[#666666]" />
              ) : (
                <ChevronDown className="w-5 h-5 text-[#666666]" />
              )}
            </button>

            {allConferencesExpanded && (
              <>
                {instancesLoading ? (
                  <div className="space-y-4">
                    {[...Array(4)].map((_, i) => (
                      <div key={i} className="animate-pulse">
                        <div className="h-28 bg-[#F5F5F5] rounded-lg"></div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(groupedConferences).map(([venueName, venueData]) => (
                      <div
                        key={venueName}
                        className="bg-white rounded-lg p-4 border border-[#E3E3E3] hover:shadow-[rgba(0,0,0,0.12)_0px_12px_20px] transition-all duration-300"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h4 className="font-bold text-sm text-[#1E1E1E]">
                              {venueName}
                            </h4>
                            <p className="text-xs text-[#666666] mt-0.5">
                              {venueData.yearRange.min} - {venueData.yearRange.max}
                            </p>
                          </div>
                          <FileText className="w-4 h-4 text-[#666666] opacity-60" />
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {venueData.instances
                            .sort((a, b) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime())
                            .map((instance) => (
                              <button
                                key={instance.instance_id}
                                onClick={() => handleInstanceClick(instance.instance_id)}
                                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-300 ${
                                  selectedInstance?.instance_id === instance.instance_id
                                    ? 'bg-black text-white'
                                    : 'bg-white text-[#1E1E1E] border border-[#E3E3E3] hover:border-black/50'
                                }`}
                              >
                                {instance.year}
                              </button>
                            ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {!instancesLoading && Object.keys(groupedConferences).length === 0 && (
                  <div className="text-center py-12">
                    <Search className="w-12 h-12 text-[#666666] mx-auto mb-4" />
                    <h3 className="text-base font-medium text-[#1E1E1E] mb-2">No conferences found</h3>
                    <p className="text-sm text-[#666666]">Try adjusting your search terms</p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default ConferenceSelectionDrawer;
