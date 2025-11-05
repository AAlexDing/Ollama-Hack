/**
 * FOFA扫描页面路由
 */
import React, { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";

import LoadingFallback from "@/components/LoadingFallback";

const FofaScanPage = lazy(() => import("@/components/fofa/ScanPage"));

const FofaPage = () => {
  return (
    <Routes>
      <Route
        element={
          <Suspense fallback={<LoadingFallback fullScreen={false} />}>
            <FofaScanPage />
          </Suspense>
        }
        path="/"
      />
    </Routes>
  );
};

export default FofaPage;

