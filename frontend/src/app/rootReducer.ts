import { combineReducers } from '@reduxjs/toolkit';
// import authSlice from "@/features/auth/authSlice"; // DISABLED - Now using React Query
import dashboardSlice from "@/features/dashboard/dashboardSlice";
import conferenceSlice from "@/features/conference/conferenceSlice";
// import notebookSlice from "@/features/notebook/notebookSlice"; // REMOVED - Now using React Query
import podcastSlice from "@/features/podcast/podcastSlice";
// import reportSlice from "@/features/report/reportSlice"; // REMOVED - Now using React Query

const rootReducer = combineReducers({
  // auth: authSlice.reducer, // DISABLED - Now using React Query for auth
  dashboard: dashboardSlice.reducer,
  conference: conferenceSlice.reducer,
  // notebook: notebookSlice.reducer, // REMOVED - Now using React Query
  podcast: podcastSlice.reducer,
  // report: reportSlice.reducer, // REMOVED - Now using React Query
});

export type RootState = ReturnType<typeof rootReducer>;
export default rootReducer;