import React from "react";
import AppLayout from "@/shared/components/layout/AppLayout";
import { useAuth } from "@/shared/hooks/useAuth";
import NotebookGridModernContainer from "@/features/notebook/components/NotebookGridModernContainer";

export default function NotebookListPage() {
  const { authChecked } = useAuth();

  if (!authChecked) {
    return (
      <AppLayout showNavigation={false}>
        <div className="min-h-screen bg-white flex items-center justify-center">
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
      <div className="min-h-screen bg-gray-50">
        <main className="w-full px-4 sm:px-6 lg:px-8 py-8">
          <NotebookGridModernContainer />
        </main>
      </div>
    </AppLayout>
  );
}

