import React, { useState, useRef, useEffect, useMemo } from "react";
import { addToast } from "@heroui/toast";
import { Key, Selection } from "@heroui/table";
import { Button } from "@heroui/button";

import EndpointDetailDrawer from "@/components/endpoints/DetailDrawer";
import CreateEndpointModal from "@/components/endpoints/CreateModal";
import EndpointTable from "@/components/endpoints/Table";
import EndpointEditModal from "@/components/endpoints/EditModal";
import { useAuth } from "@/contexts/AuthContext";
import {
  useCustomQuery,
  usePaginationUrlState,
  PaginationValidationConfig,
} from "@/hooks";
import { endpointApi } from "@/api";
import {
  EndpointWithAIModelCount,
  PageResponse,
  SortOrder,
  TaskStatusEnum,
} from "@/types";
import DashboardLayout from "@/layouts/Main";
import ErrorDisplay from "@/components/ErrorDisplay";
import { useDialog } from "@/contexts/DialogContext";
import { DeleteIcon, TestIcon } from "@/components/icons";

// 端点列表页
const EndpointListPage = () => {
  const { isAdmin } = useAuth();
  const { confirm } = useDialog();

  // 验证配置
  const [validationConfig, setValidationConfig] =
    useState<PaginationValidationConfig>({
      page: { min: 1 },
      pageSize: { min: 5, max: 100 },
      totalPages: 1,
      orderBy: {
        allowedFields: ["id", "name", "status", "created_at", "max_tps", "tps_updated_at"],
        defaultField: "id",
      },
    });

  // 使用URL参数管理状态，替代多个单独的useState
  const {
    page,
    pageSize,
    search: searchTerm,
    orderBy,
    order,
    setPage,
    setPageSize,
    setSearch: setSearchTerm,
    setOrderBy,
    setOrder,
  } = usePaginationUrlState(
    {
      page: 1,
      pageSize: 10,
      search: "",
      orderBy: "max_tps",
      order: SortOrder.DESC,
    },
    validationConfig,
  );

  // 详情抽屉状态
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedEndpointId, setSelectedEndpointId] = useState<number | null>(
    null,
  );

  // 多选状态
  const [selectedEndpointIds, setSelectedEndpointIds] = useState<Selection>(
    new Set([]),
  );

  // 新增状态变量
  const INITIAL_VISIBLE_COLUMNS = [
    "id",
    "name",
    // "url",
    "status",
    "models",
    "max_tps",
    "tps_updated_at",
    // "created_at",
    "actions",
  ];
  const [visibleColumns, setVisibleColumns] = useState<Selection>(
    new Set(INITIAL_VISIBLE_COLUMNS),
  );

  // 模态框状态
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingEndpoint, setEditingEndpoint] =
    useState<EndpointWithAIModelCount | null>(null);

  // 测试状态管理
  const [testingEndpointIds, setTestingEndpointIds] = useState<number[]>([]);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 获取端点列表
  const {
    data: endpoints,
    isLoading,
    error: endpointsError,
    refetch,
  } = useCustomQuery<PageResponse<EndpointWithAIModelCount>>(
    ["endpoints", page, searchTerm, orderBy, order, pageSize],
    () =>
      endpointApi.getEndpoints({
        page,
        size: pageSize,
        search: searchTerm,
        order_by: orderBy,
        order,
      }),
    { staleTime: 30000 },
  );

  // 当总页数变化时，更新验证配置
  useEffect(() => {
    if (endpoints?.pages) {
      setValidationConfig((prev) => ({
        ...prev,
        totalPages: endpoints.pages,
      }));
    }
  }, [endpoints?.pages]);

  useEffect(() => {
    const running_endpoint_ids = endpoints?.items
      .filter((endpoint) => endpoint.task_status === TaskStatusEnum.RUNNING)
      .map((endpoint) => endpoint.id);

    if (running_endpoint_ids && running_endpoint_ids.length > 0) {
      let new_testing_endpoint_ids = new Set([
        ...testingEndpointIds,
        ...running_endpoint_ids,
      ]);

      setTestingEndpointIds(Array.from(new_testing_endpoint_ids));
    }
  }, [endpoints, setTestingEndpointIds]);

  // 处理搜索
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    refetch();
  };

  // 处理页码变化
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  // 处理选择变化
  const handleSelectionChange = (keys: Set<Key>) => {
    setSelectedEndpointIds(keys);
  };

  // 处理批量测试端点
  const handleBatchTestEndpoints = () => {
    if (!selectedEndpointIds || selectedEndpointIds.size === 0) return;

    const endpointIds = Array.from(selectedEndpointIds).map(Number);

    confirm(
      `确定要测试选定的 ${endpointIds.length} 个端点吗？`,
      async () => {
        try {
          const result = await endpointApi.batchTestEndpoints({
            endpoint_ids: endpointIds,
          });

          // 添加到测试中的端点列表
          setTestingEndpointIds((prev) => {
            const newTestingIds = new Set([...prev]);

            endpointIds.forEach((id) => {
              if (!prev.includes(id)) {
                newTestingIds.add(id);
              }
            });

            return Array.from(newTestingIds);
          });

          addToast({
            title: "批量测试已触发",
            description: `成功: ${result.success_count}, 失败: ${result.failed_count}`,
            color: "primary",
          });

          // 清除选择
          setSelectedEndpointIds(new Set([]));
        } catch (err) {
          addToast({
            title: "批量测试失败",
            description: (err as Error).message || "请重试",
            color: "danger",
          });
        }
      },
      "确认批量测试端点",
    );
  };

  // 处理测试所有端点
  const handleTestAllEndpoints = () => {
    const totalCount = endpoints?.total || 0;
    
    confirm(
      `确定要测试所有 ${totalCount} 个端点吗？`,
      async () => {
        try {
          const result = await endpointApi.testAllEndpoints();

          // 标记当前页面的端点为测试中
          // 其他端点的状态会通过轮询机制自动更新
          const currentPageEndpointIds = endpoints?.items
            .map((ep) => ep.id)
            .filter((id): id is number => id !== undefined) || [];
          
          setTestingEndpointIds((prev) => {
            const newTestingIds = new Set([...prev, ...currentPageEndpointIds]);
            return Array.from(newTestingIds);
          });

          addToast({
            title: "测试所有端点已触发",
            description: `成功: ${result.success_count}, 失败: ${result.failed_count}`,
            color: "primary",
          });

          // 刷新列表以获取最新状态
          refetch();
        } catch (err) {
          addToast({
            title: "测试所有端点失败",
            description: (err as Error).message || "请重试",
            color: "danger",
          });
        }
      },
      "确认测试所有端点",
    );
  };

  // 处理批量删除端点
  const handleBatchDeleteEndpoints = () => {
    if (!selectedEndpointIds || selectedEndpointIds.size === 0) return;

    const endpointIds = Array.from(selectedEndpointIds).map(Number);

    confirm(
      `确定要删除选定的 ${endpointIds.length} 个端点吗？此操作不可撤销。`,
      async () => {
        try {
          const result = await endpointApi.batchDeleteEndpoints({
            endpoint_ids: endpointIds,
          });

          addToast({
            title: "批量删除成功",
            description: `成功: ${result.success_count}, 失败: ${result.failed_count}`,
            color: "success",
          });

          // 清除选择
          setSelectedEndpointIds(new Set([]));

          // 刷新列表
          refetch();
        } catch (err) {
          addToast({
            title: "批量删除失败",
            description: (err as Error).message || "请重试",
            color: "danger",
          });
        }
      },
      "确认批量删除端点",
    );
  };

  // 处理删除端点
  const handleDeleteEndpoint = async (id: number) => {
    confirm("确定要删除这个端点吗？此操作不可撤销。", async () => {
      try {
        await endpointApi.deleteEndpoint(id);
        refetch();
        setIsEditModalOpen(false);
      } catch (err) {
        addToast({
          title: "删除端点失败",
          description: (err as Error).message || "请重试",
          color: "danger",
        });
      }
    });
  };

  // 处理测试端点
  const handleTestEndpoint = (id: number) => {
    confirm(
      `确定要测试端点 ${id} 吗？`,
      async () => {
        try {
          // 直接调用函数式更新，避免 stale closure
          setTestingEndpointIds((prev) => {
            if (prev.includes(id)) {
              addToast({
                title: "测试已触发",
                description: `端点 ${id} 测试已开始，请等待结果`,
                color: "primary",
              });

              return prev;
            }
            endpointApi.triggerEndpointTest(id);
            addToast({
              title: "测试已触发",
              description: `端点 ${id} 测试已开始，请等待结果`,
              color: "primary",
            });

            return [...prev, id];
          });
        } catch (err) {
          addToast({
            title: "触发测试失败",
            description: (err as Error).message || "请重试",
            color: "danger",
          });
        }
      },
      "确认测试端点",
    );
  };

  // 创建选择工具栏内容
  const selectionToolbarContent = useMemo(() => {
    if (!selectedEndpointIds || selectedEndpointIds.size === 0) return null;

    return (
      <div className="flex gap-2">
        <Button
          color="primary"
          size="sm"
          startContent={<TestIcon />}
          variant="flat"
          onPress={handleBatchTestEndpoints}
        >
          批量测试
        </Button>
        <Button
          color="danger"
          size="sm"
          startContent={<DeleteIcon />}
          variant="flat"
          onPress={handleBatchDeleteEndpoints}
        >
          批量删除
        </Button>
      </div>
    );
  }, [selectedEndpointIds]);

  // 添加轮询逻辑
  useEffect(() => {
    // 如果有正在测试的端点，开始轮询
    if (testingEndpointIds.length > 0 && !pollingIntervalRef.current) {
      // 创建一个当前ID列表的副本，用于闭包内部使用
      const currentTestingIds = [...testingEndpointIds];

      pollingIntervalRef.current = setInterval(async () => {
        // 获取当前最新的测试ID列表
        let stillTestingIds = [...currentTestingIds];

        // 检查每个正在测试的端点的状态
        for (const endpointId of currentTestingIds) {
          try {
            const task = await endpointApi.getEndpointTask(endpointId);

            const endpoint = endpoints?.items.find(
              (endpoint) => endpoint.id === endpointId,
            );

            if (endpoint) {
              endpoint.task_status = task.status;
            }

            if (
              task.status !== TaskStatusEnum.RUNNING &&
              task.status !== TaskStatusEnum.PENDING
            ) {
              if (task.status === TaskStatusEnum.FAILED) {
                addToast({
                  title: "测试失败",
                  description: `端点 ${endpointId} 测试失败，请重试`,
                  color: "danger",
                });
              } else if (task.status === TaskStatusEnum.DONE) {
                addToast({
                  title: "测试成功",
                  description: `端点 ${endpointId} 测试成功`,
                  color: "success",
                });
              }
              // 如果没有运行中的任务，从测试列表中移除
              stillTestingIds = stillTestingIds.filter(
                (id) => Number(id) !== Number(endpointId),
              );
              // 刷新端点列表以获取最新状态
              refetch();
            }
          } catch {
            // 出错时也从列表中移除，避免无限尝试
            stillTestingIds = stillTestingIds.filter(
              (id) => Number(id) !== Number(endpointId),
            );
          }
        }

        // 更新正在测试的端点列表 - 使用函数式更新确保使用最新状态
        setTestingEndpointIds((prev) => {
          if (JSON.stringify(stillTestingIds) !== JSON.stringify(prev)) {
            return stillTestingIds;
          }

          return prev;
        });

        // 如果没有正在测试的端点，清除轮询
        if (stillTestingIds.length === 0 && pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      }, 5000); // 每5秒轮询一次
    }

    return () => {
      // 组件卸载时清除轮询
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [testingEndpointIds, refetch]);

  // 打开端点详情抽屉
  const openEndpointDetail = (endpointId: number) => {
    setSelectedEndpointId(endpointId);
    setIsDetailDrawerOpen(true);
  };

  // 关闭端点详情抽屉
  const closeEndpointDetail = () => {
    setIsDetailDrawerOpen(false);
  };

  return (
    <DashboardLayout current_root_href="/endpoints">
      {endpointsError ? (
        <ErrorDisplay
          error={
            new Error((endpointsError as Error)?.message || "加载端点列表失败")
          }
        />
      ) : (
        <EndpointTable
          endpoints={endpoints?.items}
          error={endpointsError}
          isAdmin={isAdmin}
          isLoading={isLoading}
          order={order}
          orderBy={orderBy}
          page={page}
          pageSize={pageSize}
          searchTerm={searchTerm}
          selectedKeys={selectedEndpointIds}
          selectionMode="multiple"
          selectionToolbarContent={selectionToolbarContent}
          setOrder={setOrder}
          setOrderBy={setOrderBy}
          setPageSize={setPageSize}
          setSearchTerm={setSearchTerm}
          setVisibleColumns={setVisibleColumns}
          testingEndpointIds={testingEndpointIds}
          totalItems={endpoints?.total}
          totalPages={endpoints?.pages}
          visibleColumns={visibleColumns}
          onCreateEndpoint={() => setIsCreateModalOpen(true)}
          onDeleteEndpoint={handleDeleteEndpoint}
          onEditEndpoint={(endpoint) => {
            setEditingEndpoint(endpoint);
            setIsEditModalOpen(true);
          }}
          onOpenEndpointDetail={openEndpointDetail}
          onPageChange={handlePageChange}
          onSearch={handleSearch}
          onSelectionChange={handleSelectionChange}
          onTestEndpoint={handleTestEndpoint}
          onTestAllEndpoints={handleTestAllEndpoints}
        />
      )}

      {/* 创建端点对话框 */}
      <CreateEndpointModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={refetch}
      />

      {/* 编辑端点对话框 */}
      {editingEndpoint && (
        <EndpointEditModal
          endpointId={editingEndpoint.id}
          endpointName={editingEndpoint.name}
          endpointUrl={editingEndpoint.url}
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onDelete={handleDeleteEndpoint}
          onSuccess={refetch}
        />
      )}

      {/* 端点详情抽屉 */}
      {selectedEndpointId && (
        <EndpointDetailDrawer
          id={selectedEndpointId}
          isAdmin={isAdmin}
          isOpen={isDetailDrawerOpen}
          onClose={closeEndpointDetail}
          onDelete={handleDeleteEndpoint}
          onEdit={(endpoint) => {
            setEditingEndpoint(endpoint);
            setIsEditModalOpen(true);
          }}
        />
      )}
    </DashboardLayout>
  );
};

export default EndpointListPage;
