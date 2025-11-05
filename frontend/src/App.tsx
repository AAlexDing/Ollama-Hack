import { Route, Routes } from "react-router-dom";
import { Suspense, lazy } from "react";

import ProtectedRoute from "@/components/ProtectedRoute";
import LoadingFallback from "@/components/LoadingFallback";

// 使用 React.lazy 动态导入页面组件
const LoginPage = lazy(() => import("@/pages/login"));
const InitPage = lazy(() => import("@/pages/init"));
const DashboardPage = lazy(() => import("@/pages/dashboard"));
const ProfilePage = lazy(() => import("@/pages/profile"));
const SettingsPage = lazy(() => import("@/pages/settings"));
const EndpointsPage = lazy(() => import("@/pages/endpoints"));
const ModelsPage = lazy(() => import("@/pages/models"));
const ApiKeysPage = lazy(() => import("@/pages/apikeys"));
const FofaPage = lazy(() => import("@/pages/fofa"));
const UsersPage = lazy(() => import("@/pages/users"));
const PlansPage = lazy(() => import("@/pages/plans"));
const UnauthorizedPage = lazy(() => import("@/pages/unauthorized"));
const NotFoundPage = lazy(() => import("@/pages/notfound"));

function App() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        {/* 公共路由 */}
        <Route element={<LoginPage />} path="/login" />
        <Route element={<InitPage />} path="/init" />
        <Route element={<UnauthorizedPage />} path="/unauthorized" />

        {/* 受保护路由 */}
        <Route element={<ProtectedRoute />}>
          <Route element={<DashboardPage />} path="/" />
          {/* 端点相关路由 */}
          <Route element={<EndpointsPage />} path="/endpoints/*" />
          {/* 模型相关路由 */}
          <Route element={<ModelsPage />} path="/models/*" />
          {/* API 密钥相关路由 */}
          <Route element={<ApiKeysPage />} path="/apikeys/*" />
          {/* 用户个人资料和设置路由 */}
          <Route element={<ProfilePage />} path="/profile" />
          <Route element={<SettingsPage />} path="/settings" />
        </Route>

        {/* 管理员路由 */}
        <Route element={<ProtectedRoute requireAdmin={true} />}>
          <Route element={<UsersPage />} path="/users/*" />
          <Route element={<PlansPage />} path="/plans/*" />
          <Route element={<FofaPage />} path="/fofa/*" />
        </Route>

        {/* 404 页面 */}
        <Route element={<NotFoundPage />} path="*" />
      </Routes>
    </Suspense>
  );
}

export default App;
