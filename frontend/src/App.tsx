import { Route, BrowserRouter, Routes } from "react-router-dom";
import { AccessProvider } from "./context/AccessContext";
import { StudentProvider } from "./context/StudentContext";
import { DomainSelectPage } from "./pages/DomainSelectPage";
import { LibraryPage } from "./pages/LibraryPage";
import { RepoDiscoveryPage } from "./pages/RepoDiscoveryPage";
import { StoryCatalogPage } from "./pages/StoryCatalogPage";
import { WorkspacePage } from "./pages/WorkspacePage";

function App() {
  return (
    <AccessProvider>
      <StudentProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<DomainSelectPage />} />
            <Route path="/library" element={<LibraryPage />} />
            <Route path="/discover" element={<RepoDiscoveryPage />} />
            <Route path="/stories" element={<StoryCatalogPage />} />
            <Route path="/workspace" element={<WorkspacePage />} />
          </Routes>
        </BrowserRouter>
      </StudentProvider>
    </AccessProvider>
  );
}

export default App;
