import { Route, BrowserRouter, Routes } from "react-router-dom";
import { DomainSelectPage } from "./pages/DomainSelectPage";
import { RepoDiscoveryPage } from "./pages/RepoDiscoveryPage";
import { StoryCatalogPage } from "./pages/StoryCatalogPage";
import { WorkspacePage } from "./pages/WorkspacePage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DomainSelectPage />} />
        <Route path="/discover" element={<RepoDiscoveryPage />} />
        <Route path="/stories" element={<StoryCatalogPage />} />
        <Route path="/workspace" element={<WorkspacePage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
