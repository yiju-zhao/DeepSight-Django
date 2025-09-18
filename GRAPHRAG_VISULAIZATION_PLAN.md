Based on my analysis of the GraphRAG visualizer codebase, here's a comprehensive integration plan for your React-TypeScript frontend:

## Integration Plan for GraphRAG Visualizer

### 1. **Architecture Overview**
The GraphRAG visualizer is a React-TypeScript application that visualizes Microsoft GraphRAG artifacts using parquet files. [1](#0-0)  It consists of three main tabs: file upload, graph visualization, and data tables. [2](#0-1) 

### 2. **Key Dependencies to Install**
You'll need to install the following core dependencies in your existing React-TS project: [3](#0-2) 

Key visualization libraries:
- `react-force-graph-2d` and `react-force-graph-3d` for graph rendering
- `@mui/material` for UI components
- `hyparquet` for parquet file processing
- `fuse.js` for search functionality
- `three` and `three-spritetext` for 3D rendering

### 3. **Integration Approach Options**

#### **Option A: Component-Level Integration (Recommended)**
Extract and integrate specific components into your existing app:

1. **Core Components to Extract:**
   - `GraphViewer` component for graph visualization [4](#0-3) 
   - `DataTableContainer` for tabular data display [5](#0-4) 
   - `DropZone` for file upload functionality [6](#0-5) 

2. **Custom Hooks to Include:**
   - `useFileHandler` for parquet file processing [7](#0-6) 
   - `useGraphData` for graph data transformation [8](#0-7) 

#### **Option B: Iframe Integration**
Deploy the GraphRAG visualizer separately and embed it as an iframe in your application.

#### **Option C: Microfrontend Integration**
Use module federation to load the GraphRAG visualizer as a microfrontend.

### 4. **Data Model Integration**
The visualizer expects specific data structures for graph visualization: [9](#0-8) 

Your backend needs to provide data in these formats:
- Entities, relationships, documents, text units, communities, community reports, and covariates
- Data can be provided as parquet files or transformed JSON [10](#0-9) 

### 5. **Theme Integration**
The visualizer uses Material-UI theming with dark/light mode support. [11](#0-10)  You can adapt this to match your existing theme or extract the theme configuration.

### 6. **Search and API Integration**
The visualizer supports API-based search functionality. [12](#0-11)  You can integrate this with your existing API infrastructure or use the search drawer components directly.

### 7. **Step-by-Step Implementation**

1. **Install Dependencies**: Add the required packages to your `package.json`
2. **Copy Type Definitions**: Import the model interfaces from the `models` directory
3. **Extract Components**: Copy `GraphViewer`, data processing hooks, and utility functions
4. **Configure Routing**: Integrate the visualizer routes into your existing router setup
5. **Data Pipeline**: Set up your backend to provide GraphRAG data in the expected format
6. **Styling Integration**: Adapt Material-UI themes to match your design system
7. **API Integration**: Connect search functionality to your GraphRAG API endpoints

### 8. **Configuration Considerations**
- The app supports both development mode with default file loading and production mode with file uploads [13](#0-12) 
- Graph visualization supports both 2D and 3D modes with fullscreen capabilities [14](#0-13) 
- The app includes Google Analytics integration which you may want to modify or remove [15](#0-14) 

## Notes

**Option A (Component-Level Integration)** is recommended as it gives you the most control and allows you to integrate the GraphRAG functionality seamlessly into your existing application. The visualizer's modular architecture makes it well-suited for this approach.

The visualizer processes all data locally for security and privacy [16](#0-15) , which is beneficial for sensitive data scenarios.

Consider that the visualizer is specifically designed for Microsoft GraphRAG artifacts, so ensure your data pipeline can generate compatible parquet files or transform your data to match the expected schema.

### Citations

**File:** README.md (L10-10)
```markdown
GraphRAG Visualizer is an application designed to visualize Microsoft [GraphRAG](https://github.com/microsoft/graphrag) artifacts. By uploading parquet files generated from the GraphRAG indexing pipeline, users can easily view and analyze data without needing additional software or scripts.
```

**File:** README.md (L22-22)
```markdown
- **Local Processing**: All artifacts are processed locally on your machine, ensuring data security and privacy.
```

**File:** README.md (L25-26)
```markdown

Once the [graphrag-api](https://github.com/noworneverev/graphrag-api) server is up and running, you can perform searches directly through the GraphRAG Visualizer. Simply go to the [GraphRAG Visualizer](https://noworneverev.github.io/graphrag-visualizer/) and use the search interface to query the API server. This allows you to easily search and explore data that is hosted on your local server.
```

**File:** src/app/components/GraphDataHandler.tsx (L46-58)
```typescript
  const graphData = useGraphData(
    entities,
    relationships,
    documents,
    textunits,
    communities,
    communityReports,
    covariates,
    includeDocuments,
    includeTextUnits,
    includeCommunities,
    includeCovariates
  );
```

**File:** src/app/components/GraphDataHandler.tsx (L65-70)
```typescript
  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      loadDefaultFiles();
    }
    // eslint-disable-next-line
  }, []);
```

**File:** src/app/components/GraphDataHandler.tsx (L136-140)
```typescript
      <Tabs value={tabIndex} onChange={handleChange} centered>
        <Tab label="Upload Artifacts" />
        <Tab label="Graph Visualization" />
        <Tab label="Data Tables" />
      </Tabs>
```

**File:** src/app/components/GraphDataHandler.tsx (L150-150)
```typescript
          <DropZone {...{ getRootProps, getInputProps, isDragActive }} />
```

**File:** src/app/components/GraphDataHandler.tsx (L167-194)
```typescript
          <GraphViewer
            data={graphData}
            graphType={graphType}
            isFullscreen={isFullscreen}
            onToggleFullscreen={toggleFullscreen}
            onToggleGraphType={toggleGraphType}
            includeDocuments={includeDocuments}
            includeTextUnits={includeTextUnits}
            onIncludeDocumentsChange={() =>
              setIncludeDocuments(!includeDocuments)
            }
            onIncludeTextUnitsChange={() =>
              setIncludeTextUnits(!includeTextUnits)
            }
            includeCommunities={includeCommunities}
            onIncludeCommunitiesChange={() =>
              setIncludeCommunities(!includeCommunities)
            }
            includeCovariates={includeCovariates}
            onIncludeCovariatesChange={() =>
              setIncludeCovariates(!includeCovariates)
            }
            hasDocuments={hasDocuments}
            hasTextUnits={hasTextUnits}
            hasCommunities={hasCommunities}
            hasCovariates={hasCovariates}
          />
        </Box>
```

**File:** src/app/components/GraphDataHandler.tsx (L198-211)
```typescript
        <Box sx={{ display: "flex", height: "calc(100vh - 64px)" }}>
          <DataTableContainer
            selectedTable={selectedTable}
            setSelectedTable={setSelectedTable}
            entities={entities}
            relationships={relationships}
            documents={documents}
            textunits={textunits}
            communities={communities}
            communityReports={communityReports}
            covariates={covariates}
          />
        </Box>
      )}
```

**File:** package.json (L6-35)
```json
  "dependencies": {
    "@emotion/react": "^11.13.0",
    "@emotion/styled": "^11.13.0",
    "@mui/icons-material": "^5.16.5",
    "@mui/material": "^5.16.5",
    "@testing-library/jest-dom": "^5.17.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/user-event": "^13.5.0",
    "@types/jest": "^27.5.2",
    "@types/node": "^16.18.104",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "axios": "^1.7.2",
    "fuse.js": "^7.0.0",
    "hyparquet": "^1.6.4",
    "material-react-table": "^2.13.1",
    "react": "^18.3.1",
    "react-app-rewired": "^2.2.1",
    "react-dom": "^18.3.1",
    "react-dropzone": "^14.2.3",
    "react-force-graph-2d": "^1.25.5",
    "react-force-graph-3d": "^1.24.3",
    "react-ga4": "^2.1.0",
    "react-router-dom": "^6.27.0",
    "react-scripts": "5.0.1",
    "react-table": "^7.8.0",
    "three": "^0.167.1",
    "three-spritetext": "^1.8.2",
    "typescript": "^4.9.5",
    "web-vitals": "^2.1.4"
```

**File:** src/app/components/GraphViewer.tsx (L45-50)
```typescript
interface GraphViewerProps {
  data: CustomGraphData;
  graphType: "2d" | "3d";
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  onToggleGraphType: (event: React.ChangeEvent<HTMLInputElement>) => void;
```

**File:** src/app/hooks/useFileHandler.ts (L12-30)
```typescript
const baseFileNames = [
  "entities.parquet",
  "relationships.parquet",
  "documents.parquet",
  "text_units.parquet",
  "communities.parquet",
  "community_reports.parquet",
  "covariates.parquet",
];

const baseMapping: { [key: string]: string } = {
  "entities.parquet": "entity",
  "relationships.parquet": "relationship",
  "documents.parquet": "document",
  "text_units.parquet": "text_unit",
  "communities.parquet": "community",
  "community_reports.parquet": "community_report",
  "covariates.parquet": "covariate",
};
```

**File:** src/app/hooks/useFileHandler.ts (L38-49)
```typescript
const useFileHandler = () => {
  const navigate = useNavigate();
  const [entities, setEntities] = useState<Entity[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [textunits, setTextUnits] = useState<TextUnit[]>([]);
  const [communities, setCommunities] = useState<Community[]>([]);
  const [covariates, setCovariates] = useState<Covariate[]>([]);
  const [communityReports, setCommunityReports] = useState<CommunityReport[]>(
    []
  );

```

**File:** src/app/models/custom-graph-data.ts (L9-45)
```typescript
export interface CustomNode extends NodeObject {
    uuid: string;
    id: string;
    name: string;
    type: string;
    title?: string;
    description?: string;
    human_readable_id?: number;
    graph_embedding?: number[];
    text_unit_ids?: string[];
    description_embedding?: number[];
    neighbors?: CustomNode[];
    links?: CustomLink[];
    text?: string;
    n_tokens?: number;
    document_ids?: string[];
    entity_ids?: string[];
    relationship_ids?: string[];   
    level?: number;
    raw_community?: number; 
    raw_content?: string;
    rank?: number;
    rank_explanation?: string;
    summary?: string;
    findings?: Finding[]
    full_content?: string;
    explanation?: string;
    subject_id?: string;
    object_id?: string;
    status?: string;
    start_date?: string;
    end_date?: string;
    source_text?: string;
    text_unit_id?: string;
    covariate_type?: string;
    parent?: number;
  }
```

**File:** src/app/layout/App.tsx (L30-55)
```typescript
  const theme = createTheme({
    palette: {
      mode: paletteType,
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: paletteType === "dark" ? darkScrollbar() : null,
        },
      },
      MuiPopover: {
        styleOverrides: {
          root: {
            zIndex: 1600,
          },
        },
      },
      MuiModal: {
        styleOverrides: {
          root: {
            zIndex: 1600,
          },
        },
      },
    },
  });
```

**File:** src/app/layout/App.tsx (L67-78)
```typescript
  useEffect(() => {
    const measurementId = process.env.REACT_APP_GA_MEASUREMENT_ID;
    if (measurementId) {
      ReactGA.initialize(measurementId);
      ReactGA.send({
        hitType: "pageview",
        page: window.location.pathname + window.location.search,
      });
    } else {
      console.error("Google Analytics measurement ID not found");
    }
  }, []);
```
