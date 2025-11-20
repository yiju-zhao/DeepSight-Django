import React from "react";
import { BookOpen } from "lucide-react";
import Header from "@/shared/components/layout/Header";
import Footer from "@/shared/components/layout/Footer";
import { useAuth } from "@/shared/hooks/useAuth";
import NotebookGridModernContainer from "@/features/notebook/components/NotebookGridModernContainer";
import LoadingState from "@/features/dashboard/components/LoadingState";

export default function NotebookListPage() {
  const { authChecked } = useAuth();

  if (!authChecked) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-grow pt-[var(--header-height)] flex items-center justify-center">
          <LoadingState />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <main className="flex-grow pt-[var(--header-height)]">
        {/* Modern Page Header */}
        <section className="relative bg-white border-b border-gray-100">
          <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-white/20 pointer-events-none" />
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-16 relative z-10">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2 mb-4">
                <span className="px-3 py-1 rounded-full bg-red-50 text-xs font-medium text-red-600 flex items-center gap-1">
                  <BookOpen className="w-3 h-3" />
                  Deep Dive
                </span>
              </div>
              <h1 className="text-4xl md:text-5xl font-bold text-[#1E1E1E] tracking-tight mb-4">
                Research Notebooks
              </h1>
              <p className="text-lg text-gray-500 leading-relaxed">
                Organize your research, sources, and insights in one place.
              </p>
            </div>
          </div>
        </section>

        {/* Main Content */}
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <NotebookGridModernContainer />
        </div>
      </main>

      <Footer />
    </div>
  );
}
