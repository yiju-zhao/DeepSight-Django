import React, { useState } from "react";
import { Menu, X } from "lucide-react";
import { Link } from "react-router-dom";
import { Toaster } from "@/shared/components/ui/toaster";
import Logo from "@/shared/components/common/Logo";
import Footer from "@/shared/components/common/Footer";
import AppLayout from "@/shared/components/layout/AppLayout";

export default function DatasetPage() {
  return (
    <AppLayout>
      <div className="min-h-screen bg-white flex flex-col">
        {/* Header */}
        <header className="border-b border-gray-200 p-4 flex justify-between items-center">
          <div className="flex items-center ml-16">{/* Add left margin for navigation button */}
            <Logo />
          </div>

        {/* Language Switcher */}
        <div className="relative group">
          <div className="cursor-pointer text-gray-600 text-lg flex items-center">
            <span className="text-2xl">文A</span>
          </div>
          <div className="absolute right-0 mt-2 w-32 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
            <button className="w-full flex items-center px-3 py-2 text-sm hover:bg-gray-100">
              🇺🇸 <span className="ml-2">English</span>
            </button>
            <button className="w-full flex items-center px-3 py-2 text-sm hover:bg-gray-100">
              🇨🇳 <span className="ml-2">简体中文</span>
            </button>
          </div>
        </div>
      </header>

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
