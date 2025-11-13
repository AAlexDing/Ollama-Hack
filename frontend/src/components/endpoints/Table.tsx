import React from "react";
import { Button } from "@heroui/button";
import { Chip } from "@heroui/chip";
import { SortDescriptor, Selection, Key } from "@heroui/table";
import { Tooltip } from "@heroui/tooltip";
import { Spinner } from "@heroui/spinner";

import { DataTable } from "@/components/DataTable";
import StatusBadge from "@/components/StatusBadge";
import {
  EndpointWithAIModelCount,
  EndpointStatusEnum,
  SortOrder,
} from "@/types";
import {
  DeleteIcon,
  EditIcon,
  EyeIcon,
  PlusIcon,
  TestIcon,
} from "@/components/icons";

interface EndpointTableProps {
  endpoints: EndpointWithAIModelCount[] | undefined;
  isLoading: boolean;
  error: any;
  page: number;
  pageSize: number;
  searchTerm: string;
  orderBy: string | undefined;
  order: SortOrder | undefined;
  visibleColumns: Selection;
  setVisibleColumns: (selection: Selection) => void;
  setSearchTerm: (term: string) => void;
  setPageSize: (size: number) => void;
  setOrderBy?: (orderBy: string) => void;
  setOrder?: (order: SortOrder) => void;
  onDeleteEndpoint: (id: number) => void;
  onEditEndpoint: (endpoint: EndpointWithAIModelCount) => void;
  onOpenEndpointDetail: (endpointId: number) => void;
  onCreateEndpoint: () => void;
  onPageChange: (page: number) => void;
  onSearch: (e: React.FormEvent) => void;
  onTestEndpoint: (id: number) => void;
  onTestAllEndpoints?: () => void;
  isAdmin: boolean;
  totalPages?: number;
  totalItems?: number;
  testingEndpointIds: number[];
  selectionMode?: "none" | "single" | "multiple";
  selectedKeys?: Selection;
  onSelectionChange?: (keys: Set<Key>) => void;
  selectionToolbarContent?: React.ReactNode;
}

const EndpointTable: React.FC<EndpointTableProps> = ({
  endpoints,
  isLoading,
  error,
  page,
  pageSize,
  searchTerm,
  orderBy,
  order,
  visibleColumns,
  setVisibleColumns,
  setSearchTerm,
  setPageSize,
  setOrderBy,
  setOrder,
  onDeleteEndpoint,
  onEditEndpoint,
  onOpenEndpointDetail,
  onCreateEndpoint,
  onPageChange,
  onSearch,
  onTestEndpoint,
  onTestAllEndpoints,
  isAdmin,
  totalPages,
  totalItems,
  testingEndpointIds,
  selectionMode = "none",
  selectedKeys,
  onSelectionChange,
  selectionToolbarContent,
}) => {
  // 跟踪每个端点的模型展开/折叠状态
  const [expandedEndpoints, setExpandedEndpoints] = React.useState<
    Set<number>
  >(new Set());

  // 获取端点状态
  const getEndpointStatus = (
    endpoint: EndpointWithAIModelCount,
  ): EndpointStatusEnum => {
    if (endpoint.recent_performances.length === 0) {
      return EndpointStatusEnum.UNAVAILABLE;
    }

    return endpoint.recent_performances[0].status;
  };

  // 排序状态
  const [sortDescriptor, setSortDescriptor] = React.useState<SortDescriptor>({
    column: orderBy || "id",
    direction:
      order === SortOrder.ASC
        ? "ascending"
        : order === SortOrder.DESC
          ? "descending"
          : "ascending",
  });

  // 定义表格列
  const columns = [
    { key: "id", label: "ID", allowsSorting: true },
    { key: "name", label: "名称", allowsSorting: true },
    { key: "url", label: "URL", allowsSorting: true },
    { key: "status", label: "状态", allowsSorting: true },
    { key: "models", label: "AI模型" },
    { key: "max_tps", label: "TPS", allowsSorting: true },
    { key: "tps_updated_at", label: "TPS更新时间", allowsSorting: true },
    { key: "created_at", label: "创建时间", allowsSorting: true },
    { key: "actions", label: "操作" },
  ];

  // 处理排序
  const handleSort = (descriptor: SortDescriptor) => {
    setSortDescriptor(descriptor);
    if (descriptor.column) {
      const newOrderBy = descriptor.column.toString();
      const newOrder =
        descriptor.direction === "ascending" ? SortOrder.ASC : SortOrder.DESC;

      // 更新父组件中的排序状态
      if (orderBy !== newOrderBy || order !== newOrder) {
        setOrderBy &&
          typeof setOrderBy === "function" &&
          setOrderBy(newOrderBy);
        setOrder && typeof setOrder === "function" && setOrder(newOrder);
      }
    }
  };

  const EndpointActionCell = ({
    endpoint,
    isTesting,
    onTestEndpoint,
    onEditEndpoint,
    onDeleteEndpoint,
    onOpenEndpointDetail,
    isAdmin,
  }) => {
    return (
      <div className="relative flex items-center gap-2">
        <Tooltip content="查看端点">
          <Button
            isIconOnly
            className="text-default-400 active:opacity-50 text-lg"
            variant="light"
            onPress={() => {
              if (endpoint.id) {
                onOpenEndpointDetail(endpoint.id);
              }
            }}
          >
            <EyeIcon />
          </Button>
        </Tooltip>
        {isAdmin && (
          <>
            <Tooltip content="测试端点">
              <Button
                isIconOnly
                className="text-default-400 active:opacity-50 text-lg"
                isLoading={isTesting}
                spinner={<Spinner color="warning" size="sm" variant="wave" />}
                variant="light"
                onPress={() => {
                  if (endpoint.id) {
                    onTestEndpoint(endpoint.id);
                  }
                }}
              >
                <TestIcon />
              </Button>
            </Tooltip>
            <Tooltip content="编辑端点">
              <Button
                isIconOnly
                className="text-default-400 active:opacity-50 text-lg"
                variant="light"
                onPress={() => onEditEndpoint(endpoint)}
              >
                <EditIcon />
              </Button>
            </Tooltip>
            <Tooltip color="danger" content="删除端点">
              <Button
                isIconOnly
                className="text-default-400 active:opacity-50 text-lg"
                variant="light"
                onPress={() => {
                  if (endpoint.id) {
                    onDeleteEndpoint(endpoint.id);
                  }
                }}
              >
                <DeleteIcon />
              </Button>
            </Tooltip>
          </>
        )}
      </div>
    );
  };

  // 渲染单元格内容
  const renderCell = (
    endpoint: EndpointWithAIModelCount,
    columnKey: string,
  ) => {
    switch (columnKey) {
      case "id":
        return endpoint.id;
      case "name":
        return (
          <span className="whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
            {endpoint.name}
          </span>
        );
      case "url":
        return (
          <div className="flex flex-col">
            <p className="text-bold text-small">{endpoint.url}</p>
          </div>
        );
      case "status":
        return <StatusBadge status={getEndpointStatus(endpoint)} />;
      case "models":
        const aiModels = endpoint.ai_models || [];
        if (aiModels.length === 0) {
          return (
            <span className="text-default-400 text-sm">
              {endpoint.avaliable_ai_model_count} / {endpoint.total_ai_model_count}
            </span>
          );
        }
        
        // 分离可用模型和需要折叠的模型（不可用、fake、未知）
        const availableModels = aiModels.filter(
          (model) => model.status === "available"
        );
        const hiddenModels = aiModels.filter(
          (model) =>
            model.status !== "available" &&
            model.status !== "unavailable" &&
            model.status !== "missing" &&
            model.status !== "fake"
        );
        const unavailableModels = aiModels.filter(
          (model) =>
            model.status === "unavailable" ||
            model.status === "missing" ||
            model.status === "fake"
        );
        
        const endpointId = endpoint.id;
        const isHovered = endpointId
          ? expandedEndpoints.has(endpointId)
          : false;
        
        const handleMouseEnter = () => {
          if (endpointId) {
            const newExpanded = new Set(expandedEndpoints);
            newExpanded.add(endpointId);
            setExpandedEndpoints(newExpanded);
          }
        };
        
        const handleMouseLeave = () => {
          if (endpointId) {
            const newExpanded = new Set(expandedEndpoints);
            newExpanded.delete(endpointId);
            setExpandedEndpoints(newExpanded);
          }
        };
        
        const totalHidden = unavailableModels.length + hiddenModels.length;
        
        return (
          <div
            className="flex flex-wrap gap-1 w-full"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
          >
            {/* 显示可用模型 */}
            {availableModels.map((model, index) => (
              <Chip
                key={`${model.name}-${model.tag}-${index}`}
                color="success"
                size="sm"
                variant="flat"
                className="font-mono"
              >
                {model.name}:{model.tag}
              </Chip>
            ))}
            
            {/* 显示不可用/fake/未知模型（根据hover状态） */}
            {isHovered && (
              <>
                {unavailableModels.map((model, index) => {
                  let chipColor: "danger" | "warning" = "danger";
                  if (model.status === "fake") {
                    chipColor = "warning"; // 黄色（假/蜜罐）
                  }
                  
                  return (
                    <Chip
                      key={`${model.name}-${model.tag}-unavailable-${index}`}
                      color={chipColor}
                      size="sm"
                      variant="flat"
                      className="font-mono"
                    >
                      {model.name}:{model.tag}
                    </Chip>
                  );
                })}
                {hiddenModels.map((model, index) => (
                  <Chip
                    key={`${model.name}-${model.tag}-hidden-${index}`}
                    color="default"
                    size="sm"
                    variant="flat"
                    className="font-mono"
                  >
                    {model.name}:{model.tag}
                  </Chip>
                ))}
              </>
            )}
          </div>
        );
      case "max_tps":
        return endpoint.max_tps !== null && endpoint.max_tps !== undefined
          ? `${endpoint.max_tps.toFixed(2)}`
          : "-";
      case "tps_updated_at":
        return endpoint.tps_updated_at
          ? new Date(endpoint.tps_updated_at + "Z").toLocaleString()
          : "-";
      case "created_at":
        return endpoint.created_at
          ? new Date(endpoint.created_at + "Z").toLocaleString()
          : "-";
      case "actions":
        return (
          <EndpointActionCell
            endpoint={endpoint}
            isAdmin={isAdmin}
            isTesting={testingEndpointIds.includes(endpoint.id)}
            onDeleteEndpoint={onDeleteEndpoint}
            onEditEndpoint={onEditEndpoint}
            onOpenEndpointDetail={onOpenEndpointDetail}
            onTestEndpoint={() => {
              if (endpoint.id) {
                onTestEndpoint(endpoint.id);
              }
            }}
          />
        );
      default:
        return null;
    }
  };

  // 顶部操作按钮内容
  const topActionContent = isAdmin && onTestAllEndpoints ? (
    <Button
      color="primary"
      startContent={<TestIcon />}
      variant="flat"
      onPress={onTestAllEndpoints}
    >
      测试所有端点
    </Button>
  ) : undefined;

  return (
    <DataTable<EndpointWithAIModelCount>
      key={testingEndpointIds.join(",")}
      addButtonProps={
        isAdmin
          ? {
              tooltip: "添加端点",
              onClick: onCreateEndpoint,
              isIconOnly: true,
            }
          : undefined
      }
      columns={columns}
      data={endpoints || []}
      topActionContent={topActionContent}
      emptyContent={
        <>
          <p className="text-xl">暂无端点数据</p>
          {isAdmin && (
            <Tooltip
              color="primary"
              content="添加第一个端点"
              placement="bottom"
            >
              <Button
                isIconOnly
                className="mt-4"
                color="primary"
                onPress={onCreateEndpoint}
              >
                <PlusIcon />
              </Button>
            </Tooltip>
          )}
        </>
      }
      error={error}
      isLoading={isLoading}
      page={page}
      pages={totalPages}
      renderCell={renderCell}
      searchPlaceholder="搜索模型..."
      searchTerm={searchTerm}
      selectedKeys={selectedKeys}
      selectedSize={pageSize}
      selectionMode={selectionMode}
      selectionToolbarContent={selectionToolbarContent}
      setSearchTerm={setSearchTerm}
      setSize={setPageSize}
      setVisibleColumns={setVisibleColumns}
      sortDescriptor={sortDescriptor}
      title="端点列表"
      total={totalItems}
      visibleColumns={visibleColumns}
      onPageChange={onPageChange}
      onSearch={onSearch}
      onSelectionChange={onSelectionChange}
      onSortChange={handleSort}
    />
  );
};

export default EndpointTable;
