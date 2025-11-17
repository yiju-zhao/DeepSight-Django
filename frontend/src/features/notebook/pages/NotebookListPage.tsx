import React from "react";
import AppLayout from "@/shared/components/layout/AppLayout";
import { useAuth } from "@/shared/hooks/useAuth";
import NotebookGridModernContainer from "@/features/notebook/components/NotebookGridModernContainer";
import MainPageHeader from "@/shared/components/common/MainPageHeader";
import { BookOpen } from "lucide-react";

export default function NotebookListPage() {
  const { authChecked } = useAuth();

  if (!authChecked) {
    return (
      <AppLayout showNavigation={false}>
        <div className="min-h-screen bg-transparent flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="flex flex-col min-h-screen bg-transparent">
        <MainPageHeader
          label="DEEPDIVE"
          title="Research Notebooks"
          subtitle="Organize your research, sources, and insights in one place"
          icon={<BookOpen className="w-6 h-6 text-[#CE0E2D]" />}
        />
        <main className="flex-1 px-4 md:px-10 lg:px-20 py-10 md:py-20">
          <div className="max-w-7xl mx-auto">
            <NotebookGridModernContainer />
          </div>
        </main>
      </div>
    </AppLayout>
  );
}
