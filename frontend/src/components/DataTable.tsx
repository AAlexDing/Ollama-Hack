import React, { ReactNode, useMemo, useState } from "react";
import {
  Table,
  TableHeader,
  TableBody,
  TableColumn,
  TableRow,
  TableCell,
  SortDescriptor,
  Selection,
  Key,
} from "@heroui/table";
import { Button } from "@heroui/button";
import {
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  DropdownSection,
} from "@heroui/dropdown";
import { Tooltip } from "@heroui/tooltip";
import { Input } from "@heroui/input";

import LoadingSpinner from "./LoadingSpinner";
import ErrorDisplay from "./ErrorDisplay";
import SearchForm from "./SearchForm";
import { PlusIcon } from "./icons";
import Pagination from "./Pagination";

// ChevronDownIcon组件
const ChevronDownIcon = ({
  strokeWidth = 1.5,
  ...otherProps
}: { strokeWidth?: number } & React.SVGProps<SVGSVGElement>) => {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      focusable="false"
      height="1em"
      role="presentation"
      viewBox="0 0 24 24"
      width="1em"
      {...otherProps}
    >
      <path
        d="m19.92 8.95-6.52 6.52c-.77.77-2.03.77-2.8 0L4.08 8.95"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeMiterlimit={10}
        strokeWidth={strokeWidth}
      />
    </svg>
  );
};

// 列定义类型
export interface Column {
  key: string;
  label: string;
  allowsSorting?: boolean;
}

// 添加按钮属性类型
export interface AddButtonProps {
  tooltip?: string;
  onClick: () => void;
  label?: string;
  isIconOnly?: boolean;
}

// DataTable组件属性类型
export interface DataTableProps<T> {
  title: string;
  columns: Column[];
  data: T[];
  total?: number;
  page: number;
  pages?: number;
  pageSize?: number;
  onPageChange: (page: number) => void;
  sortDescriptor: SortDescriptor;
  onSortChange: (descriptor: SortDescriptor) => void;
  isLoading?: boolean;
  error?: Error;
  searchTerm?: string;
  searchPlaceholder?: string;
  onSearch?: (e: React.FormEvent) => void;
  setSearchTerm?: (value: string) => void;
  renderCell: (item: T, columnKey: string) => ReactNode;
  emptyContent?: ReactNode;
  addButtonProps?: AddButtonProps;
  visibleColumns?: Selection;
  setVisibleColumns?: (selection: Selection) => void;
  selectedSize?: number;
  setSize?: (size: number) => void;
  autoSearchDelay?: number;
  removeWrapper?: boolean;
  topActionContent?: ReactNode;
  minPageSize?: number; // 最小页面大小
  maxPageSize?: number; // 最大页面大小
  // 多选相关属性
  selectionMode?: "none" | "single" | "multiple";
  selectedKeys?: Selection;
  onSelectionChange?: (keys: Set<Key>) => void;
  selectionToolbarContent?: ReactNode;
  showJumper?: boolean;
  showCustomPageSize?: boolean;
}

// 通用DataTable组件
export const DataTable = <T extends { id?: number | string }>({
  title,
  columns,
  data,
  total,
  page,
  pages = 1,
  pageSize = 10,
  onPageChange,
  sortDescriptor,
  onSortChange,
  isLoading = false,
  error,
  searchTerm = "",
  searchPlaceholder = "搜索...",
  onSearch,
  setSearchTerm,
  renderCell,
  emptyContent,
  addButtonProps,
  visibleColumns = new Set(columns.map((col) => col.key)),
  setVisibleColumns,
  selectedSize = pageSize,
  setSize,
  autoSearchDelay = 0,
  removeWrapper = false,
  topActionContent,
  minPageSize = 5,
  maxPageSize = 100,
  // 多选相关属性
  selectionMode = "none",
  selectedKeys,
  onSelectionChange,
  selectionToolbarContent,
  showJumper = true,
  showCustomPageSize = true,
}: DataTableProps<T>) => {
  // 获取表头列
  const headerColumns = React.useMemo(() => {
    if (visibleColumns === "all") return columns;

    return columns.filter((column) =>
      Array.from(visibleColumns).includes(column.key),
    );
  }, [visibleColumns, columns]);

  // 每页行数
  const pageSizeOptions = [5, 10, 15, 30, 50];
  const [pageSizeSelectedKeys, setPageSizeSelectedKeys] = useState(
    pageSizeOptions.includes(selectedSize)
      ? new Set([selectedSize.toString()])
      : new Set(["custom"]),
  );

  // 自定义页面大小
  const [customPageSize, setCustomPageSize] = useState<string>(
    selectedSize.toString(),
  );

  // 验证自定义页面大小的函数
  const validateCustomPageSize = (value: string): boolean => {
    return (
      value.match(/^\d+$/) &&
      Number(value) >= minPageSize &&
      Number(value) <= maxPageSize
    );
  };

  // 判断自定义页面大小是否无效
  const isInvalidCustomPageSize = useMemo(() => {
    return !validateCustomPageSize(customPageSize);
  }, [customPageSize, minPageSize, maxPageSize]);

  // 处理自定义页面大小应用
  const applyCustomPageSize = () => {
    if (isInvalidCustomPageSize) {
      return;
    }

    const customPageSizeNumber = Number(customPageSize);

    setSize?.(customPageSizeNumber);
    if (pageSizeOptions.includes(customPageSizeNumber)) {
      setPageSizeSelectedKeys(new Set([customPageSize]));
    } else {
      setPageSizeSelectedKeys(new Set(["custom"]));
    }

    setCustomPageSize(customPageSize);
    onPageChange(1);
  };

  // 处理回车键应用自定义页面大小
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      applyCustomPageSize();
    }
  };

  // 底部内容区域
  const bottomContent = React.useMemo(() => {
    return (
      <div className="py-2 px-2 flex justify-between items-center flex-col gap-3">
        {pages > 1 && (
          <Pagination
            currentPage={page}
            showJumper={showJumper}
            totalPages={pages}
            onPageChange={onPageChange}
          />
        )}
      </div>
    );
  }, [
    pages,
    page,
    onPageChange,
    selectedSize,
    setSize,
    total,
    data.length,
    pageSize,
    customPageSize,
    minPageSize,
    maxPageSize,
  ]);

  // 顶部内容区域
  const topContent = React.useMemo(() => {
    return (
      <div className="flex justify-between flex-col gap-3 w-full">
        <div className="flex justify-between gap-3 items-end w-full">
          {setSearchTerm && onSearch && (
            <SearchForm
              autoSearchDelay={autoSearchDelay}
              handleSearch={onSearch}
              placeholder={searchPlaceholder}
              searchTerm={searchTerm}
              setSearchTerm={setSearchTerm}
            />
          )}
          <div className="flex gap-3">
            {setVisibleColumns && (
              <Dropdown>
                <DropdownTrigger className="hidden sm:flex">
                  <Button
                    endContent={<ChevronDownIcon className="text-small" />}
                    variant="flat"
                  >
                    选择列
                  </Button>
                </DropdownTrigger>
                <DropdownMenu
                  disallowEmptySelection
                  aria-label="显示的列"
                  closeOnSelect={false}
                  selectedKeys={visibleColumns}
                  selectionMode="multiple"
                  onSelectionChange={setVisibleColumns}
                >
                  {columns.map((column) => (
                    <DropdownItem key={column.key} className="capitalize">
                      {column.label}
                    </DropdownItem>
                  ))}
                </DropdownMenu>
              </Dropdown>
            )}
            {topActionContent}
            {addButtonProps && (
              <Tooltip
                color="primary"
                content={addButtonProps.tooltip || "添加"}
              >
                <Button
                  color="primary"
                  isIconOnly={addButtonProps.isIconOnly || false}
                  size={addButtonProps.isIconOnly ? undefined : "md"}
                  onPress={addButtonProps.onClick}
                >
                  {addButtonProps.label || <PlusIcon />}
                </Button>
              </Tooltip>
            )}
          </div>
        </div>
        {pages > 1 && (
          <div className="flex justify-between items-center flex-wrap gap-2 w-full">
            {setSize && (
              <Dropdown>
                <DropdownTrigger>
                  {/* <Button
                    className="text-default-400 text-small"
                    endContent={<ChevronDownIcon className="text-small" />}
                    variant="light"
                  >
                    每页行数: {selectedSize}
                  </Button> */}
                  <div className="flex items-center gap-1 text-default-400 text-small ml-2 cursor-pointer">
                    <span>每页行数: {selectedSize}</span>
                    <ChevronDownIcon />
                  </div>
                </DropdownTrigger>
                <DropdownMenu
                  disallowEmptySelection
                  aria-label="每页行数"
                  closeOnSelect={true}
                  selectedKeys={pageSizeSelectedKeys}
                  selectionMode="single"
                  onSelectionChange={(e) => {
                    const key = e.currentKey;

                    // 不再需要处理"custom"选项，因为已经整合到下拉菜单中
                    if (key && key !== "custom") {
                      setSize(Number(key));
                      setPageSizeSelectedKeys(new Set([key]));
                      setCustomPageSize(key);
                      onPageChange(1);
                    }
                  }}
                >
                  <DropdownSection showDivider title="预设大小">
                    {pageSizeOptions.map((size) => (
                      <DropdownItem key={size}>{size}</DropdownItem>
                    ))}
                  </DropdownSection>
                  {showCustomPageSize && (
                    <DropdownSection title="自定义">
                      <DropdownItem
                        isReadOnly
                        endContent={
                          <Button
                            color="primary"
                            size="sm"
                            variant="flat"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              applyCustomPageSize();
                            }}
                          >
                            应用
                          </Button>
                        }
                        startContent={
                          <Input
                            aria-label="自定义页面大小"
                            className="w-20"
                            color={
                              isInvalidCustomPageSize ? "danger" : "default"
                            }
                            errorMessage={`页面大小必须在 ${minPageSize} 到 ${maxPageSize} 之间`}
                            isInvalid={isInvalidCustomPageSize}
                            placeholder={`${minPageSize}-${maxPageSize}`}
                            radius="sm"
                            size="sm"
                            value={customPageSize}
                            onKeyDown={handleKeyDown}
                            onValueChange={setCustomPageSize}
                          />
                        }
                        textValue="自定义页面大小"
                      />
                    </DropdownSection>
                  )}
                </DropdownMenu>
              </Dropdown>
            )}

            <span className="text-default-400 text-small mr-2">
              共 {total || data.length} 条记录
            </span>
          </div>
        )}
        {selectionMode === "multiple" &&
          selectedKeys &&
          selectedKeys.size > 0 && (
            <div className="w-full flex justify-between items-center">
              <span className="text-default-400 text-small ml-2">
                已选择 {selectedKeys.size} 项
              </span>
              {selectionToolbarContent}
            </div>
          )}
      </div>
    );
  }, [
    searchTerm,
    searchPlaceholder,
    setSearchTerm,
    onSearch,
    columns,
    visibleColumns,
    setVisibleColumns,
    addButtonProps,
    autoSearchDelay,
    selectionMode,
    selectedKeys,
    selectionToolbarContent,
    pages,
    setSize,
    selectedSize,
    pageSizeSelectedKeys,
    customPageSize,
    isInvalidCustomPageSize,
    minPageSize,
    maxPageSize,
    applyCustomPageSize,
    handleKeyDown,
  ]);

  // 渲染表格
  const renderTable = () => (
    <Table
      isHeaderSticky
      aria-label={title}
      bottomContent={bottomContent}
      bottomContentPlacement="outside"
      // classNames={{
      //   wrapper: "max-h-[600px]",
      // }}
      removeWrapper={removeWrapper}
      selectedKeys={selectedKeys}
      selectionMode={selectionMode}
      sortDescriptor={sortDescriptor}
      topContent={topContent}
      topContentPlacement="outside"
      onSelectionChange={(selection) => {
        if (selection === "all") {
          onSelectionChange?.(new Set(data.map((item) => item.id?.toString())));
        } else {
          onSelectionChange?.(selection);
        }
      }}
      onSortChange={onSortChange}
    >
      <TableHeader columns={headerColumns}>
        {(column) => (
          <TableColumn key={column.key} allowsSorting={column.allowsSorting}>
            {column.label}
          </TableColumn>
        )}
      </TableHeader>
      <TableBody
        emptyContent={emptyContent || <p className="text-xl">暂无数据</p>}
        isLoading={isLoading}
        items={data}
        loadingContent={
          <div className="flex justify-center py-8">
            <LoadingSpinner size="large" />
          </div>
        }
      >
        {(item) => (
          <TableRow key={item.id?.toString()}>
            {(columnKey) => (
              <TableCell>{renderCell(item, columnKey.toString())}</TableCell>
            )}
          </TableRow>
        )}
      </TableBody>
    </Table>
  );

  // 主要渲染逻辑
  return (
    <div className="w-full">
      {error ? (
        <ErrorDisplay error={new Error(error?.message || `加载${title}失败`)} />
      ) : (
        renderTable()
      )}
    </div>
  );
};
