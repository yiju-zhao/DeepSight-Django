import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Database, BarChart2, Search, Mic, FileText, Users } from "lucide-react";
import Header from "../layout/Header";
import Footer from "../layout/Footer";

const HomePage = () => {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <main className="flex-grow pt-[var(--header-height)]">
        {/* Hero Section */}
        <section className="relative overflow-hidden bg-white">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-gray-100 via-white to-white opacity-50"></div>
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-32 relative z-10">
            <div className="max-w-4xl">
              <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-foreground mb-8 animate-slide-up">
                Unlock the Power of <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-black to-gray-600">
                  Deep Intelligence
                </span>
              </h1>
              <p className="text-xl md:text-2xl text-muted-foreground mb-10 max-w-2xl animate-slide-up-delay-1 leading-relaxed">
                DeepSight provides advanced analytics, comprehensive datasets, and deep learning insights to empower your research and decision-making.
              </p>
              <div className="flex flex-wrap gap-4 animate-slide-up-delay-2">
                <Link
                  to="/dashboard"
                  className="px-8 py-4 bg-black text-white text-base font-semibold rounded-lg hover:bg-accent-red transition-colors duration-300 shadow-huawei-md hover:shadow-huawei-lg flex items-center btn-arrow"
                >
                  Explore Dashboard
                </Link>
                <Link
                  to="/dataset"
                  className="px-8 py-4 bg-white text-foreground border border-gray-200 text-base font-semibold rounded-lg hover:border-black transition-colors duration-300 flex items-center"
                >
                  View Datasets
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="py-24 bg-gray-50">
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">Comprehensive Intelligence Suite</h2>
              <p className="text-lg text-muted-foreground">
                Everything you need to analyze, understand, and leverage data effectively.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {/* Feature 1: Dashboard */}
              <Link to="/dashboard" className="group">
                <div className="bg-white p-8 rounded-2xl shadow-huawei-sm hover:shadow-huawei-md transition-all duration-300 card-hoverable h-full border border-transparent hover:border-gray-100">
                  <div className="w-12 h-12 bg-black/5 rounded-xl flex items-center justify-center mb-6 group-hover:bg-accent-red/10 transition-colors">
                    <BarChart2 className="w-6 h-6 text-foreground group-hover:text-accent-red transition-colors" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 group-hover:text-accent-red transition-colors">Analytics Dashboard</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    Real-time visualization and analytics of your data streams. Monitor key metrics and trends at a glance.
                  </p>
                </div>
              </Link>

              {/* Feature 2: Dataset */}
              <Link to="/dataset" className="group">
                <div className="bg-white p-8 rounded-2xl shadow-huawei-sm hover:shadow-huawei-md transition-all duration-300 card-hoverable h-full border border-transparent hover:border-gray-100">
                  <div className="w-12 h-12 bg-black/5 rounded-xl flex items-center justify-center mb-6 group-hover:bg-accent-red/10 transition-colors">
                    <Database className="w-6 h-6 text-foreground group-hover:text-accent-red transition-colors" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 group-hover:text-accent-red transition-colors">Dataset Management</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    Access and manage vast collections of structured and unstructured data for your machine learning models.
                  </p>
                </div>
              </Link>

              {/* Feature 3: Deepdive */}
              <Link to="/deepdive" className="group">
                <div className="bg-white p-8 rounded-2xl shadow-huawei-sm hover:shadow-huawei-md transition-all duration-300 card-hoverable h-full border border-transparent hover:border-gray-100">
                  <div className="w-12 h-12 bg-black/5 rounded-xl flex items-center justify-center mb-6 group-hover:bg-accent-red/10 transition-colors">
                    <Search className="w-6 h-6 text-foreground group-hover:text-accent-red transition-colors" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 group-hover:text-accent-red transition-colors">Deepdive Analysis</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    Perform in-depth analysis using advanced notebooks. Explore data relationships and uncover hidden patterns.
                  </p>
                </div>
              </Link>

              {/* Feature 4: Conference */}
              <Link to="/conference" className="group">
                <div className="bg-white p-8 rounded-2xl shadow-huawei-sm hover:shadow-huawei-md transition-all duration-300 card-hoverable h-full border border-transparent hover:border-gray-100">
                  <div className="w-12 h-12 bg-black/5 rounded-xl flex items-center justify-center mb-6 group-hover:bg-accent-red/10 transition-colors">
                    <Users className="w-6 h-6 text-foreground group-hover:text-accent-red transition-colors" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 group-hover:text-accent-red transition-colors">Conference Hub</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    Stay updated with the latest conferences, sessions, and academic gatherings in the AI field.
                  </p>
                </div>
              </Link>

              {/* Feature 5: Reports */}
              <Link to="/report" className="group">
                <div className="bg-white p-8 rounded-2xl shadow-huawei-sm hover:shadow-huawei-md transition-all duration-300 card-hoverable h-full border border-transparent hover:border-gray-100">
                  <div className="w-12 h-12 bg-black/5 rounded-xl flex items-center justify-center mb-6 group-hover:bg-accent-red/10 transition-colors">
                    <FileText className="w-6 h-6 text-foreground group-hover:text-accent-red transition-colors" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 group-hover:text-accent-red transition-colors">Intelligence Reports</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    Generate and view comprehensive reports summarizing your data analysis and insights.
                  </p>
                </div>
              </Link>

              {/* Feature 6: Podcasts */}
              <Link to="/podcast" className="group">
                <div className="bg-white p-8 rounded-2xl shadow-huawei-sm hover:shadow-huawei-md transition-all duration-300 card-hoverable h-full border border-transparent hover:border-gray-100">
                  <div className="w-12 h-12 bg-black/5 rounded-xl flex items-center justify-center mb-6 group-hover:bg-accent-red/10 transition-colors">
                    <Mic className="w-6 h-6 text-foreground group-hover:text-accent-red transition-colors" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 group-hover:text-accent-red transition-colors">AI Podcasts</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    Listen to curated podcasts discussing the latest trends and breakthroughs in artificial intelligence.
                  </p>
                </div>
              </Link>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-24 bg-black text-white">
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-6">Ready to dive deeper?</h2>
            <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
              Join thousands of researchers and developers using DeepSight to transform their data into actionable intelligence.
            </p>
            <Link
              to="/signup"
              className="inline-block px-8 py-4 bg-accent-red text-white text-base font-semibold rounded-lg hover:bg-accent-red-hover transition-colors duration-300 shadow-lg hover:shadow-xl"
            >
              Start Your Journey
            </Link>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
};

export default HomePage;
