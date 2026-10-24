import React, { Suspense, lazy } from "react";
import { App as AntApp, ConfigProvider, Spin } from "antd";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppProvider } from "./AppContext";
import AppLayout from "./components/AppLayout";
import ChatPage from "./pages/ChatPage";

// Loaded only when the directory is opened
const DirectoryPage = lazy(() => import("./pages/DirectoryPage"));

const theme = {
  token: {
    colorPrimary: "#4f46e5",
    borderRadius: 10,
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  },
};

const App: React.FC = () => (
  <ConfigProvider theme={theme}>
    <AntApp>
      <AppProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<Navigate to="/chat" replace />} />
              {/* one route for both, so sending the first message (which adds the id) keeps the page mounted */}
              <Route path="chat/:threadId?" element={<ChatPage />} />
              <Route
                path="directory"
                element={
                  <Suspense fallback={<div className="h-full flex items-center justify-center"><Spin /></div>}>
                    <DirectoryPage />
                  </Suspense>
                }
              />
              <Route path="*" element={<Navigate to="/chat" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AppProvider>
    </AntApp>
  </ConfigProvider>
);

export default App;
