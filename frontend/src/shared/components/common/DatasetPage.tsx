import React from "react";
import { Database } from "lucide-react";
import { Toaster } from "@/shared/components/ui/toaster";
import Header from "@/shared/components/layout/Header";
import Footer from "@/shared/components/layout/Footer";
import LanguageSwitcher from "@/shared/components/common/LanguageSwitcher";

export default function DatasetPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <main className="flex-grow pt-[var(--header-height)]">
        {/* Modern Page Header */}
        <section className="relative bg-white border-b border-gray-100">
          <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-white/20 pointer-events-none" />
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2 mb-4">
                <span className="px-3 py-1 rounded-full bg-blue-50 text-xs font-medium text-blue-600 flex items-center gap-1">
                  <Database className="w-3 h-3" />
                  Research Data
                </span>
              </div>
              <div className="flex items-center justify-between">
                <h1 className="text-4xl md:text-5xl font-bold text-[#1E1E1E] tracking-tight mb-4">
                  Dataset
                </h1>
                <div className="mb-4">
                  <LanguageSwitcher />
                </div>
              </div>
              <p className="text-lg text-gray-500 leading-relaxed">
                Explore and manage research papers and datasets.
              </p>
            </div>
          </div>
        </section>

        {/* Main Content */}
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">Research Papers</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(9)].map((_, idx) => (
              <div
                key={idx}
                className="border border-gray-200 rounded-lg shadow-sm p-4 h-48 flex items-center justify-center text-gray-400 bg-white hover:shadow-md transition-shadow"
              >
                Empty Paper Card
              </div>
            ))}
          </div>
        </div>
      </main>


      <Toaster />
    </div>
  );
}
