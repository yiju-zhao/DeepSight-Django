import React, { useState } from "react";
import { Database } from "lucide-react";
import { Toaster } from "@/shared/components/ui/toaster";
import Footer from "@/shared/components/common/Footer";
import AppLayout from "@/shared/components/layout/AppLayout";
import MainPageHeader from "@/shared/components/common/MainPageHeader";
import LanguageSwitcher from "@/shared/components/common/LanguageSwitcher";

export default function DatasetPage() {
  return (
    <AppLayout>
      <div className="min-h-screen bg-transparent flex flex-col">
        <MainPageHeader
          title="Dataset"
          icon={<Database className="w-5 h-5 text-white" />}
          iconColor="from-green-500 to-green-600"
          rightActions={<LanguageSwitcher />}
        />

      {/* Main Content */}
      <main className="flex-1 px-6 py-8">
        <h2 className="text-2xl font-semibold text-gray-800 mb-6">Research Papers</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(9)].map((_, idx) => (
            <div
              key={idx}
              className="border border-gray-200 rounded-lg shadow-sm p-4 h-48 flex items-center justify-center text-gray-400"
            >
              Empty Paper Card
            </div>
          ))}
        </div>
      </main>

        <Footer />
        <Toaster />
      </div>
    </AppLayout>
  );
}
