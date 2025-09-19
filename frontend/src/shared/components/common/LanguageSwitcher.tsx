import React from "react";

/**
 * Language switcher component for use in page headers
 * Provides English/Chinese language selection with dropdown
 */
const LanguageSwitcher: React.FC = () => {
  return (
    <div className="relative group">
      <div className="cursor-pointer text-gray-600 text-lg flex items-center p-2 rounded-lg hover:bg-gray-100 transition-colors">
        <span className="text-xl">文A</span>
      </div>
      <div className="absolute right-0 mt-2 w-32 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
        <button className="w-full flex items-center px-3 py-2 text-sm hover:bg-gray-100">
          🇺🇸 <span className="ml-2">English</span>
        </button>
        <button className="w-full flex items-center px-3 py-2 text-sm hover:bg-gray-100">
          🇨🇳 <span className="ml-2">中文</span>
        </button>
      </div>
    </div>
  );
};

export default LanguageSwitcher;
