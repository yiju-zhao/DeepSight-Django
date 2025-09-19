import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from '@/app/store';
import { Toaster } from "@/shared/components/ui/toaster";
import { ErrorBoundary } from "@/shared/components/ui/ErrorBoundary";
import { QueryProvider } from "@/shared/providers/QueryProvider";
import { PerformanceMonitor, reportWebVitals } from "@/shared/utils/performance";
import { PrivateRoute } from "@/shared/components/auth/PrivateRoute";
import { useAuth } from "@/shared/hooks/useAuth";
import {
  HomePage,
  DatasetPage,
  NotebookListPage,
  DeepdivePage,
  DashboardPage,
  ConferencePage,
  ConferenceDashboard,
  ReportPage,
  PodcastPage,
  OrganizationPage,
  LoginPage,
  SignupPage,
  preloadCriticalRoutes,
} from "@/features/routes/LazyRoutes";

function AppRoutes() {
  // Initialize authentication check
  useAuth();
  
  // Preload critical routes on mount
  useEffect(() => {
    preloadCriticalRoutes().catch(console.warn);
  }, []);

  return (
    <Routes>
      <Route path="/" element={<HomePage.Component />} />
      <Route 
        path="/dataset" 
        element={
          <PrivateRoute>
            <DatasetPage.Component />
          </PrivateRoute>
        } 
      />
      <Route 
        path="/deepdive" 
        element={
          <PrivateRoute>
            <NotebookListPage.Component />
          </PrivateRoute>
        } 
      />
      <Route 
        path="/deepdive/:notebookId" 
        element={
          <PrivateRoute>
            <DeepdivePage.Component />
          </PrivateRoute>
        } 
      />
      <Route 
        path="/dashboard" 
        element={
          <PrivateRoute>
            <DashboardPage.Component />
          </PrivateRoute>
        } 
      />
      <Route path="/conference" element={<ConferencePage.Component />} />
      <Route
        path="/dashboard/conference"
        element={
          <PrivateRoute>
            <ConferenceDashboard.Component />
          </PrivateRoute>
        }
      />
      <Route path="/report" element={<ReportPage.Component />} />
      <Route path="/podcast" element={<PodcastPage.Component />} />
      <Route path="/organization" element={<OrganizationPage.Component />} />
      <Route path="/login" element={<LoginPage.Component />} />
      <Route path="/signup" element={<SignupPage.Component />} />
    </Routes>
  );
}

function App() {
  useEffect(() => {
    // Initialize performance monitoring
    const monitor = PerformanceMonitor.getInstance();
    monitor.startMonitoring('navigation');
    monitor.startMonitoring('paint');
    monitor.startMonitoring('resource');

    // Report Web Vitals
    reportWebVitals((metric) => {
      console.log('Web Vital:', metric);
    });

    return () => {
      monitor.disconnect();
    };
  }, []);

  return (
    <Provider store={store}>
      <QueryProvider>
        <ErrorBoundary level="page">
          <AppRoutes />
          <Toaster />
        </ErrorBoundary>
      </QueryProvider>
    </Provider>
  );
}

export default App;