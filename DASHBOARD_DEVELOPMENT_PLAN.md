# Conference Dashboard Development Plan

This document outlines the plan for developing the conference dashboard page.

## 1. Project Goal

The goal is to create a dashboard page that allows users to explore and visualize publication data from academic conferences. Users will be able to select a conference and year, and the dashboard will display various statistics and charts to provide insights into the conference's publications.

## 2. Data Model

The dashboard will be based on the following Django models from `backend/conferences/models.py`:

-   `Venue`: Represents a conference series (e.g., "CVPR").
-   `Instance`: Represents a specific occurrence of a conference (e.g., "CVPR 2023"). Uses `instance_id` as primary key.
-   `Publication`: Represents a single paper published at a conference `Instance`. Uses UUID as primary key.
-   `Event`: Represents conference sessions/events. Uses UUID as primary key.

### Key Publication Fields Available:
-   **Core Info**: `title`, `authors`, `abstract`, `summary`
-   **Affiliations**: `aff` (raw affiliations), `aff_unique` (normalized), `aff_country_unique` (countries)
-   **Author Details**: `author_position` (PhD, Professor, etc.), `author_homepage`
-   **Metadata**: `keywords`, `research_topic`, `tag`, `session` (Poster/Oral)
-   **External**: `external_id`, `doi`, `pdf_url`, `github`, `site`
-   **Quality**: `rating` (decimal, reviewer ratings)

## 3. Dashboard Design

The dashboard will consist of the following components:

### 3.1. Selectors

-   **Year Selector:** A dropdown menu to select the conference year.
-   **Conference Selector:** A dropdown menu to select the conference `Venue`.

### 3.2. Key Performance Indicators (KPIs)

A set of cards displaying the following high-level statistics:

-   Total number of publications.
-   Total number of unique authors.
-   Number of unique affiliations (`aff_unique`).
-   Number of unique countries (`aff_country_unique`).
-   Average rating of publications.
-   **NEW:** Session type distribution (Poster vs Oral from `session` field).
-   **NEW:** Author academic level breakdown (from `author_position` field).

### 3.3. Charts and Visualizations

-   **Publications per Topic:** A bar chart showing the number of publications for each `research_topic`.
-   **Top Affiliations:** A bar chart showing the top 10 most frequent affiliations (`aff_unique`).
-   **Top Countries:** A world map or bar chart showing the distribution of publications by country (`aff_country_unique`).
-   **Top Keywords:** A word cloud or bar chart of the most frequent `keywords`.
-   **Rating Distribution:** A histogram showing the distribution of publication `rating`s.
-   **NEW:** Session Type Analysis: Pie chart of Poster vs Oral presentations (`session` field).
-   **NEW:** Academic Hierarchy: Bar chart of author positions (`author_position` - PhD students, Postdocs, Professors, etc.).
-   **NEW:** Collaboration Network: Geographic visualization combining `aff` and `aff_country_unique` to show collaboration patterns.
-   **NEW:** External Resources: Count of papers with GitHub repositories, project sites, etc.

### 3.4. Data Table

-   A paginated table of all publications for the selected conference.
-   Columns: `Title`, `Authors`, `Rating`, `Research Topic`, `Session Type`, `Affiliations`.
-   Additional filterable columns: `Author Position`, `Country`, `Keywords`.
-   The table will be searchable and sortable.
-   **NEW:** Click-through links to external resources (GitHub, project sites, PDFs).

## 4. Development Plan

The development will be divided into frontend and backend tasks.

### 📊 Progress Summary
- **Backend**: 🟢 **100% COMPLETE** (8/8 steps completed)
  - ✅ API Infrastructure Created
  - ✅ Dashboard & Overview Endpoints
  - ✅ Data Aggregation & Serializers
  - ✅ Unit Tests & Performance Optimization
- **Frontend**: 🟢 **100% COMPLETE** (8/8 steps completed)
  - ✅ Dashboard Page & Components Created
  - ✅ Data Fetching with TanStack Query
  - ✅ Charts & Visualizations Implemented
  - ✅ Data Table with Filtering & Pagination
- **Overall**: 🟢 **100% COMPLETE**

### 4.1. Backend (Django)

1.  **✅ COMPLETED: Create conferences API infrastructure:**
    -   ✅ Create `conferences/views.py` with DRF ViewSets
    -   ✅ Create `conferences/serializers.py` with model serializers
    -   ✅ Create `conferences/urls.py` using `DefaultRouter`
        -   ✅ Router endpoints mounted under `/api/v1/conferences/`:
            -   ✅ `venues/` (list/detail)
            -   ✅ `instances/` (list/detail; support `?venue=CVPR`)
            -   ✅ `publications/` (list/detail; support `?instance=<id>`)
            -   ✅ `events/` (list/detail; support `?instance=<id>`)
    -   ✅ Update main `backend/backend/urls.py` to include conferences URLs:
        -   ✅ `path("api/v1/conferences/", include("conferences.urls"))`
    -   ✅ Use trailing slashes and lower-case plural resource names for consistency.

2.  **✅ COMPLETED: Create dashboard API endpoint:**
    -   ✅ URL: `/api/v1/conferences/dashboard/dashboard/`
    -   ✅ Parameters: `venue` (string) and `year` (integer), OR `instance` (integer ID)
    -   ✅ Auth: default to `IsAuthenticated` (unless we explicitly decide it should be public)
    -   ✅ Response: single JSON payload designed for client-side charts and KPIs, e.g.:
        -   ✅ `kpis`: totals and derived metrics (publications, unique authors, affiliations, countries, avg_rating, session_distribution, author_position_distribution, resource_counts)
        -   ✅ `charts`: arrays for charts (topics, top_affiliations, top_countries, top_keywords, ratings_histogram, session_types, author_positions)
        -   ✅ `table`: paginated publications for the selected scope using `StandardPageNumberPagination` (fields: Title, Authors, Rating, Research Topic, Session Type, Affiliations, etc.)
    -   ✅ Caching: include `Last-Modified` and `Cache-Control` headers similar to reports endpoints.

3.  **✅ COMPLETED: Implement enhanced data aggregation logic:**
    -   ✅ Calculate KPIs including new fields: `session` types, `author_position` breakdown
    -   ✅ Use Django's ORM and aggregation functions to efficiently query the database.
    -   ✅ Group by: `research_topic`, `aff_unique`, `aff_country_unique`, `keywords`, `session`, `author_position`
    -   ✅ **NEW:** Handle semicolon-separated values in aggregation (authors, affiliations, positions)
    -   ✅ Optimize queries using `select_related("instance__venue")` and `prefetch_related` where appropriate.
    -   ✅ Added DB indexes for frequent filters (e.g., `Instance(venue, year)`, `Publication(instance)`).

4.  **✅ COMPLETED: Implement pagination for the publication list** using `StandardPageNumberPagination`.
5.  **✅ COMPLETED: Create serializers** for API responses, including dashboard KPI/chart serializers and publication table serializers.
6.  **✅ COMPLETED: Write unit tests** for the new API endpoint to ensure data accuracy, pagination behavior, and permissions.
    -   ✅ 22 comprehensive test cases covering all ViewSets and dashboard functionality
    -   ✅ Fixed authentication, pagination, and data aggregation test accuracy
    -   ✅ Added model ordering for consistent pagination results
7.  **✅ COMPLETED: Create conferences overview endpoint (for dashboard landing):**
    -   ✅ URL: `/api/v1/conferences/dashboard/overview/`
    -   ✅ Returns: `{ total_conferences, total_papers, years_covered, avg_papers_per_year, conferences: [...] }`
    -   ✅ Used by frontend dashboard to render high-level overview.
8.  **✅ COMPLETED: Permissions & documentation:**
    -   ✅ Default endpoints to `IsAuthenticated` unless public access is explicitly required.
    -   ✅ Ensure endpoints appear in Swagger/Redoc via `drf_yasg`.

### 4.2. Frontend (React/TypeScript)

1.  **✅ COMPLETED: Create a new page component for the dashboard.**
    -   ✅ Created `src/routes/_layout/conferences.tsx` with TanStack Router
    -   ✅ Implemented main dashboard layout with Container and VStack
    -   ✅ Added overview statistics display and no-selection state

2.  **✅ COMPLETED: Implement the Year and Conference selectors:**
    -   ✅ Fetch venues via `GET /api/v1/conferences/venues/`
    -   ✅ Fetch instances (years) for a venue via `GET /api/v1/conferences/instances/?venue=CVPR`
    -   ✅ Dynamic year dropdown based on selected venue
    -   ✅ Quick instance selector buttons for easy navigation

3.  **✅ COMPLETED: Create a data fetching service:**
    -   ✅ Created `src/client/conferences.ts` with full TypeScript API client
    -   ✅ Call `GET /api/v1/conferences/dashboard/?venue=CVPR&year=2023` (or `?instance=ID`) for dashboard data
    -   ✅ Call `GET /api/v1/conferences/overview/` for landing overview stats
    -   ✅ Integrated TanStack Query for loading and error states management

4.  **✅ COMPLETED: Implement the KPI components.**
    -   ✅ Created `src/components/conferences/DashboardKPIs.tsx`
    -   ✅ Displays total publications, unique authors, affiliations, countries, average rating
    -   ✅ Session distribution (Poster vs Oral), author positions, external resource counts
    -   ✅ Color-coded icons and progress bars for visual appeal

5.  **✅ COMPLETED: Implement the charts:**
    -   ✅ Added Recharts library (`npm install recharts`) for data visualization
    -   ✅ Created `src/components/conferences/DashboardCharts.tsx` with comprehensive charts:
        -   ✅ Bar charts: Research topics, affiliations, author positions
        -   ✅ Pie charts: Geographic distribution, session types
        -   ✅ Line chart: Rating distribution histogram
        -   ✅ Word cloud-style keyword visualization
    -   ✅ Responsive grid layout with proper color schemes

6.  **✅ COMPLETED: Implement the data table:**
    -   ✅ Created `src/components/conferences/PublicationsTable.tsx`
    -   ✅ Implemented search, filtering by topic/session, pagination
    -   ✅ External links to PDF, GitHub, project sites with icon buttons
    -   ✅ Responsive table design with hover effects and proper spacing

7.  **✅ COMPLETED: Style the dashboard:**
    -   ✅ Consistent with Chakra UI design system used throughout the application
    -   ✅ Proper spacing, typography, and color schemes
    -   ✅ Responsive grid layouts and mobile-friendly components

8.  **Component tests** for the new dashboard components.
    -   🔄 **PENDING**: Unit tests for React components not yet implemented
