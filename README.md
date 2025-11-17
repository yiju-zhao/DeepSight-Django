# DeepSight Django/React Application

A modern full-stack application for research and document analysis, built with Django REST Framework backend and React TypeScript frontend.

## 🏗️ Architecture Overview

### Backend (Django)
- **Django REST Framework** for API endpoints
- **Celery** for background task processing
- **Modular Django apps** for notebooks, reports, podcasts, conferences
- **Custom exception handling** with normalized error responses
- **Service layer architecture** with dedicated service classes
- **Agent-based processing** with STORM report generation

### Frontend (React + TypeScript)
- **React 18** with TypeScript for type safety
- **React Query (TanStack Query)** for server state management
- **Redux Toolkit** for UI-only state (theme, modals, etc.)
- **React Router** for client-side routing
- **Tailwind CSS** for styling
- **Vitest + React Testing Library** for testing
- **Storybook** for component documentation

## 🚀 Key Features

### Modern State Management
- **React Query** handles all server state with caching, optimistic updates, and background refetching
- **Redux** limited to UI-only state (theme, sidebar, notifications)
- **Centralized query keys** prevent cache collisions
- **Feature-scoped custom hooks** encapsulate query logic

### Robust Testing Infrastructure
- **Vitest** for fast unit and integration tests
- **MSW (Mock Service Worker)** for reliable API mocking
- **React Testing Library** for component testing
- **Comprehensive test utilities** with provider wrappers

### Performance Optimizations
- **React.memo** and **useMemo** for preventing unnecessary re-renders
- **Database query optimization** with select_related and prefetch_related
- **Code splitting** for smaller bundle sizes
- **Optimistic updates** for better user experience

### Agent Architecture
The application includes sophisticated agent-based processing:

- **STORM Agent** (report_agent): Modularized research report generation
  - `config.py` - Configuration and model setup
  - `io_operations.py` - File I/O and data processing
  - `runner_orchestrator.py` - Pipeline orchestration
  - Preserves lazy imports and macOS safety for Celery integration

## 📁 Project Structure

```
DeepSight-Django/
├── backend/
│   ├── core/                    # Core Django settings and utilities
│   ├── agents/                  # Agent-based processing modules
│   │   └── report_agent/        # STORM research report generation
│   ├── notebooks/               # Notebook management
│   ├── reports/                 # Report generation and management
│   ├── podcasts/                # Podcast processing
│   └── conferences/             # Conference data management
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # App configuration and store
│   │   ├── features/            # Feature-based modules
│   │   │   ├── auth/            # Authentication (React Query)
│   │   │   ├── dashboard/       # Dashboard with performance optimization
│   │   │   ├── notebook/        # Notebook management (React Query)
│   │   │   ├── report/          # Report generation (React Query)
│   │   │   ├── podcast/         # Podcast features
│   │   │   └── conference/      # Conference management
│   │   ├── shared/              # Shared utilities and components
│   │   │   ├── api/             # Consolidated API client
│   │   │   ├── components/      # Reusable UI components
│   │   │   ├── hooks/           # Custom React hooks
│   │   │   ├── queries/         # Centralized query keys and utilities
│   │   │   └── utils/           # Utility functions
│   │   └── test-utils/          # Testing utilities and mocks
│
├── stories/                     # Storybook stories
└── docs/                        # Additional documentation
```

## 🛠️ Development Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- Redis (for Celery)
- PostgreSQL (recommended) or SQLite for development

### Backend Setup

1. **Create virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development tools
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database and API keys
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server:**
   ```bash
   python manage.py runserver
   ```

7. **Start Celery worker (separate terminal):**
   ```bash
   celery -A backend worker -l info
   ```

### Frontend Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Run tests:**
   ```bash
   npm run test
   ```

4. **Start Storybook:**
   ```bash
   npm run storybook
   ```

## 🧪 Testing

### Backend Testing
```bash
cd backend
pytest                          # Run all tests
pytest --cov                    # Run with coverage
pytest -x                       # Stop on first failure
```

### Frontend Testing
```bash
cd frontend
npm run test                     # Run tests in watch mode
npm run test:ci                  # Run tests once (CI mode)
npm run test:coverage            # Run with coverage report
```

### Code Quality
```bash
# Backend
cd backend
make lint                        # Run black, ruff, mypy
make format                      # Auto-format code

# Frontend
cd frontend
npm run lint                     # ESLint
npm run type-check               # TypeScript checking
```

## 🔄 State Management Patterns

### Server State (React Query)
```typescript
// Feature-scoped custom hooks
export function useNotebooks() {
  return useQuery({
    queryKey: queryKeys.notebooks.list(),
    queryFn: () => apiClient.get('/api/notebooks/'),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Mutations with optimistic updates
export function useCreateNotebook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => apiClient.post('/api/notebooks/', data),
    onSuccess: (newNotebook) => {
      queryClient.setQueryData(
        queryKeys.notebooks.list(),
        (old) => [newNotebook, ...old]
      );
    },
  });
}
```

### UI State (Redux)
```typescript
// Limited to UI-only concerns
const uiSlice = createSlice({
  name: 'ui',
  initialState: {
    theme: 'light',
    sidebarOpen: true,
    notifications: [],
  },
  reducers: {
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
    },
  },
});
```

## 📚 API Documentation

### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/refresh/` - Refresh token

### Notebooks
- `GET /api/notebooks/` - List notebooks
- `POST /api/notebooks/` - Create notebook
- `GET /api/notebooks/{id}/` - Get notebook details
- `PUT /api/notebooks/{id}/` - Update notebook
- `DELETE /api/notebooks/{id}/` - Delete notebook

### Reports
- `GET /api/reports/` - List reports
- `POST /api/reports/generate/` - Generate new report
- `GET /api/reports/{id}/` - Get report details
- `DELETE /api/reports/{id}/` - Delete report
- `POST /api/reports/{id}/cancel/` - Cancel report generation

### Error Handling
All API responses follow a consistent error format:
```json
{
  "detail": "Human-readable error message",
  "error_code": "VALIDATION_ERROR",
  "field_errors": {
    "email": ["This field is required."]
  }
}
```

## 🎨 UI Components

### Shared Components
- **Button** - Consistent button styling with variants
- **Modal** - Accessible modal dialogs
- **Alert** - Status messages and notifications
- **LoadingSpinner** - Loading states
- **Badge** - Status indicators

### Feature Components
- **NotebookCard** - Notebook display with actions
- **ReportList** - Report listing with filtering
- **SourceUploader** - File upload interface

## 🔧 Environment Variables

### Backend (.env)
```bash
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379/0

# API Keys for agents
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
GOOGLE_API_KEY=AIza...
```

### Frontend (.env.local)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=DeepSight
```

## 🚀 Deployment

### Backend (Django)
1. Configure production settings
2. Set up PostgreSQL database
3. Configure Redis for Celery
4. Set environment variables
5. Run migrations
6. Collect static files
7. Deploy with gunicorn + nginx

### Frontend (React)
1. Build production bundle: `npm run build`
2. Deploy to static hosting (Vercel, Netlify) or serve with nginx
3. Configure API base URL for production

## 🤝 Contributing

1. **Code Style**: Follow existing patterns and use the provided linting tools
2. **Testing**: Add tests for new features and bug fixes
3. **Documentation**: Update relevant documentation for API or architecture changes
4. **Pull Requests**: Use descriptive titles and include context in descriptions

### Development Workflow
1. Create feature branch from `main`
2. Make changes with tests
3. Run linting and tests
4. Create pull request
5. Code review and merge

## 📄 License

This project is proprietary and confidential.

---

For more detailed information, see the [REFACTORING_PLAN.md](REFACTORING_PLAN.md) for the complete modernization journey and architectural decisions.
