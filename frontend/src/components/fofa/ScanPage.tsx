/**
 * FOFA扫描页面组件 - 使用HeroUI
 */
import type {
  FofaScanRequest,
  FofaScanInfo,
  SubscriptionRequest,
  SubscriptionInfo,
} from "@/types";

import React, { useState, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@heroui/button";
import { Card, CardBody, CardHeader } from "@heroui/card";
import { Input, Textarea } from "@heroui/input";
import { Select, SelectItem } from "@heroui/select";
import { Switch } from "@heroui/switch";
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
} from "@heroui/table";
import { Chip } from "@heroui/chip";
import { Progress } from "@heroui/progress";
import { addToast } from "@heroui/toast";

import { fofaApi, subscriptionApi } from "@/api";
import DashboardLayout from "@/layouts/Main";
import { SearchIcon, RefreshIcon } from "@/components/icons";

// 国家选项（常用国家）
const COUNTRY_OPTIONS = [
  { key: "US", label: "美国 (US)" },
  { key: "CN", label: "中国 (CN)" },
  { key: "JP", label: "日本 (JP)" },
  { key: "DE", label: "德国 (DE)" },
  { key: "GB", label: "英国 (GB)" },
  { key: "FR", label: "法国 (FR)" },
  { key: "KR", label: "韩国 (KR)" },
  { key: "RU", label: "俄罗斯 (RU)" },
  { key: "SG", label: "新加坡 (SG)" },
  { key: "AU", label: "澳大利亚 (AU)" },
];

// 状态颜色映射
const STATUS_COLOR_MAP: Record<
  string,
  "default" | "primary" | "success" | "warning" | "danger"
> = {
  pending: "default",
  running: "primary",
  completed: "success",
  failed: "danger",
};

const STATUS_TEXT_MAP: Record<string, string> = {
  pending: "等待中",
  running: "扫描中",
  completed: "已完成",
  failed: "失败",
};

const FofaScanPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [autoRefresh, setAutoRefresh] = useState(true);

  // FOFA扫描表单状态
  const [country, setCountry] = useState("US");
  const [customQuery, setCustomQuery] = useState("");
  const [autoTest, setAutoTest] = useState(true);
  const [testDelay, setTestDelay] = useState("5");

  // 订阅表单状态
  const [subscriptionUrl, setSubscriptionUrl] = useState(
    "https://awesome-ollama-server.vercel.app/data.json"
  );
  const [pullInterval, setPullInterval] = useState("300");

  // 进度轮询状态
  const [pullingSubscriptionId, setPullingSubscriptionId] = useState<
    number | null
  >(null);
  
  // 用于防止重复显示 Toast
  const lastCompletedSubscriptionRef = useRef<number | null>(null);

  // 获取扫描历史
  const {
    data: scanHistory,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["fofa-scans"],
    queryFn: () => fofaApi.getScanHistory({ limit: 50, offset: 0 }),
    refetchInterval: autoRefresh ? 5000 : false, // 自动刷新5秒
  });

  // 获取订阅列表
  const {
    data: subscriptionList,
    isLoading: isLoadingSubscriptions,
    refetch: refetchSubscriptions,
  } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: () =>
      subscriptionApi.getSubscriptionList({ limit: 10, offset: 0 }),
    refetchInterval: autoRefresh ? 5000 : false,
  });

  // 监听 pullingSubscriptionId 变化
  React.useEffect(() => {
    console.log("[状态监听] pullingSubscriptionId 变化:", pullingSubscriptionId);
  }, [pullingSubscriptionId]);

  // 订阅进度轮询
  const { data: subscriptionProgress } = useQuery({
    queryKey: ["subscription-progress", pullingSubscriptionId],
    queryFn: () => subscriptionApi.getProgress(pullingSubscriptionId!),
    refetchInterval: (data) => {
      // 如果数据还没加载，继续轮询
      if (!data) {
        return 2000;
      }

      // 调试：打印状态
      console.log("[订阅进度-轮询] 当前状态:", data.status, "进度:", data.progress_current, "/", data.progress_total);

      // 如果状态为 PULLING 或 PROCESSING，继续轮询
      if (data.status === "pulling" || data.status === "processing" || data.status === "idle") {
        return 2000; // 2秒轮询
      }

      // 完成或失败时，停止轮询（状态清除在 useEffect 中处理）
      if (data.status === "completed" || data.status === "failed") {
        console.log("[订阅进度-轮询] 检测到完成/失败状态，返回 false 停止轮询");
        return false; // 停止轮询
      }

      // 其他状态，继续轮询
      return 2000;
    },
    enabled: pullingSubscriptionId !== null,
  });

  // 监听进度数据变化，处理完成/失败状态
  React.useEffect(() => {
    if (!subscriptionProgress || !pullingSubscriptionId) return;

    console.log("[订阅进度-Effect] 数据变化:", subscriptionProgress.status, "订阅ID:", subscriptionProgress.subscription_id);

    // 防止重复处理同一个订阅的完成状态
    if (lastCompletedSubscriptionRef.current === subscriptionProgress.subscription_id) {
      console.log("[订阅进度-Effect] 该订阅已处理过，跳过");
      return;
    }

    // 当检测到完成或失败状态时，清除轮询 ID
    if (subscriptionProgress.status === "completed" || subscriptionProgress.status === "failed") {
      console.log("[订阅进度-Effect] 检测到完成/失败，准备清除状态");
      
      // 标记为已处理
      lastCompletedSubscriptionRef.current = subscriptionProgress.subscription_id;
      
      // 显示完成提示
      if (subscriptionProgress.status === "completed") {
        addToast({
          title: "订阅拉取完成",
          description: subscriptionProgress.progress_message || "订阅拉取成功",
          color: "success",
          duration: 3000,
        });
      } else if (subscriptionProgress.status === "failed") {
        addToast({
          title: "订阅拉取失败",
          description: subscriptionProgress.error_message || subscriptionProgress.progress_message || "订阅拉取失败",
          color: "danger",
          duration: 5000,
        });
      }

      // 立即清除状态
      console.log("[订阅进度-Effect] 立即清除 pullingSubscriptionId");
      setPullingSubscriptionId(null);
      queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
    }
  }, [subscriptionProgress, pullingSubscriptionId, addToast, queryClient]);

  // 启动扫描
  const startScanMutation = useMutation({
    mutationFn: (data: FofaScanRequest) => fofaApi.startScan(data),
    onSuccess: (response) => {
      addToast({
        title: "扫描已启动",
        description: `扫描ID: ${response.scan_id}`,
        color: "success",
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ["fofa-scans"] });
      // 重置表单
      setCountry("US");
      setCustomQuery("");
      setAutoTest(true);
      setTestDelay("5");
    },
    onError: (error: any) => {
      addToast({
        title: "扫描启动失败",
        description: error.response?.data?.detail || error.message,
        color: "danger",
        duration: 5000,
      });
    },
  });

  // 创建订阅
  const createSubscriptionMutation = useMutation({
    mutationFn: (data: SubscriptionRequest) =>
      subscriptionApi.createSubscription(data),
    onSuccess: (response) => {
      // 重置完成标记，允许新的拉取
      lastCompletedSubscriptionRef.current = null;
      
      addToast({
        title: "订阅已创建",
        description: response.message,
        color: "success",
        duration: 3000,
      });
      // 确保轮询已启动（如果 onMutate 没触发）
      if (pullingSubscriptionId !== response.subscription_id) {
        setPullingSubscriptionId(response.subscription_id);
      }
      // 重置表单
      setSubscriptionUrl("https://awesome-ollama-server.vercel.app/data.json");
      setPullInterval("300");
    },
    onError: (error: any) => {
      // 出错时停止轮询
      setPullingSubscriptionId(null);
      addToast({
        title: "订阅创建失败",
        description: error.response?.data?.detail || error.message,
        color: "danger",
        duration: 5000,
      });
    },
  });

  // 手动拉取订阅
  const pullSubscriptionMutation = useMutation({
    mutationFn: (subscriptionId: number) =>
      subscriptionApi.pullSubscription(
        subscriptionId,
        parseInt(testDelay) || 5
      ),
    onMutate: (subscriptionId) => {
      // 重置完成标记，允许新的拉取
      lastCompletedSubscriptionRef.current = null;
      // 立即启动进度轮询（在请求发送时）
      console.log("[手动拉取] onMutate - 设置轮询ID:", subscriptionId);
      setPullingSubscriptionId(subscriptionId);
    },
    onSuccess: (response, subscriptionId) => {
      // 后台任务已启动，继续轮询
      console.log("[手动拉取] onSuccess - 后台任务已启动:", response.message, "当前轮询ID:", subscriptionId);
    },
    onError: (error: any, subscriptionId) => {
      // 出错时停止轮询
      console.log("[手动拉取] onError - 停止轮询");
      setPullingSubscriptionId(null);
      addToast({
        title: "订阅拉取失败",
        description: error.response?.data?.detail || error.message,
        color: "danger",
        duration: 5000,
      });
    },
    onSettled: (data, error, subscriptionId) => {
      console.log("[手动拉取] onSettled - 请求已完成, 当前pullingSubscriptionId:", pullingSubscriptionId);
    },
  });

  // 提交FOFA扫描表单
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const requestData: FofaScanRequest = {
      country,
      custom_query: customQuery || null,
      auto_test: autoTest,
      test_delay_seconds: parseInt(testDelay) || 5,
    };

    startScanMutation.mutate(requestData);
  };

  // 提交订阅表单
  const handleSubscriptionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const requestData: SubscriptionRequest = {
      url: subscriptionUrl,
      pull_interval: parseInt(pullInterval) || 300,
    };

    createSubscriptionMutation.mutate(requestData);
  };

  // 渲染状态单元格
  const renderStatusCell = (scan: FofaScanInfo) => {
    const color = STATUS_COLOR_MAP[scan.status] || "default";
    const text = STATUS_TEXT_MAP[scan.status] || scan.status;

    return (
      <Chip color={color} size="sm" variant="flat">
        {text}
      </Chip>
    );
  };

  // 渲染时间
  const renderDate = (dateString: string | null) => {
    if (!dateString) return "-";

    return new Date(dateString).toLocaleString("zh-CN");
  };

  // 获取当前订阅（最新的一个）
  const currentSubscription: SubscriptionInfo | null =
    subscriptionList && subscriptionList.length > 0
      ? subscriptionList[0]
      : null;

  return (
    <DashboardLayout current_root_href="/fofa">
      <div className="flex flex-col gap-4 p-4">
        {/* 扫描和订阅卡片 - 横向并排 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* FOFA扫描卡片 */}
          <Card>
            <CardHeader className="flex gap-3 items-center justify-between">
              <div className="flex flex-col">
                <p className="text-lg font-semibold">主动扫描</p>
                <p className="text-sm text-default-500">
                  自动发现全球范围内的 Ollama 服务
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-default-500">自动刷新:</span>
                <Switch
                  isSelected={autoRefresh}
                  size="sm"
                  onValueChange={setAutoRefresh}
                />
                <Button
                  isIconOnly
                  size="sm"
                  variant="light"
                  onPress={() => refetch()}
                >
                  <RefreshIcon />
                </Button>
              </div>
            </CardHeader>
            <CardBody>
              <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
                <Select
                  isRequired
                  description="选择要扫描的国家，系统会搜索该国家的Ollama服务"
                  label="目标国家"
                  placeholder="选择国家"
                  selectedKeys={[country]}
                  onChange={(e) => setCountry(e.target.value)}
                >
                  {COUNTRY_OPTIONS.map((option) => (
                    <SelectItem key={option.key} value={option.key}>
                      {option.label}
                    </SelectItem>
                  ))}
                </Select>

                <Textarea
                  description="高级用户可以自定义FOFA查询语句"
                  label="自定义查询（可选）"
                  minRows={2}
                  placeholder='例如: app="Ollama" && city="Beijing"'
                  value={customQuery}
                  onChange={(e) => setCustomQuery(e.target.value)}
                />

                <div className="flex items-center gap-2">
                  <Switch
                    isSelected={autoTest}
                    size="sm"
                    onValueChange={setAutoTest}
                  >
                    自动触发检测
                  </Switch>
                  <span className="text-xs text-default-500">
                    扫描完成后自动对发现的端点进行性能检测
                  </span>
                </div>

                <Input
                  isRequired
                  description="扫描完成后等待多少秒再开始检测"
                  label="检测延迟（秒）"
                  max="300"
                  min="0"
                  placeholder="5"
                  type="number"
                  value={testDelay}
                  onChange={(e) => setTestDelay(e.target.value)}
                />

                <Button
                  fullWidth
                  color="primary"
                  isLoading={startScanMutation.isPending}
                  startContent={!startScanMutation.isPending && <SearchIcon />}
                  type="submit"
                >
                  启动扫描
                </Button>
              </form>
            </CardBody>
          </Card>

          {/* 订阅卡片 */}
          <Card>
            <CardHeader className="flex gap-3 items-center justify-between">
              <div className="flex flex-col">
                <p className="text-lg font-semibold">订阅</p>
                <p className="text-sm text-default-500">
                  从订阅地址自动拉取 Ollama 服务列表
                </p>
              </div>
              <Button
                isIconOnly
                size="sm"
                variant="light"
                onPress={() => refetchSubscriptions()}
              >
                <RefreshIcon />
              </Button>
            </CardHeader>
            <CardBody>
              <form
                className="flex flex-col gap-4"
                onSubmit={handleSubscriptionSubmit}
              >
                <Input
                  isRequired
                  description="订阅JSON数据源的URL地址"
                  label="订阅地址"
                  placeholder="https://awesome-ollama-server.vercel.app/data.json"
                  value={subscriptionUrl}
                  onChange={(e) => setSubscriptionUrl(e.target.value)}
                />

                <Input
                  isRequired
                  description="自动拉取订阅的时间间隔（60-86400秒）"
                  label="拉取间隔（秒）"
                  max="86400"
                  min="60"
                  placeholder="300"
                  type="number"
                  value={pullInterval}
                  onChange={(e) => setPullInterval(e.target.value)}
                />

                <Button
                  fullWidth
                  color="primary"
                  isLoading={createSubscriptionMutation.isPending}
                  type="submit"
                >
                  创建/更新订阅
                </Button>
              </form>

              {/* 当前订阅信息 */}
              {currentSubscription && (
                <div className="mt-4 pt-4 border-t border-default-200">
                  <div className="flex flex-col gap-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-default-500">上次拉取:</span>
                      <span className="font-medium">
                        {currentSubscription.last_pull_at
                          ? new Date(
                              currentSubscription.last_pull_at
                            ).toLocaleString("zh-CN")
                          : "从未拉取"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-default-500">拉取间隔:</span>
                      <span className="font-medium">
                        {currentSubscription.pull_interval} 秒
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-default-500">上次新增:</span>
                      <span className="font-medium text-success">
                        {currentSubscription.last_pull_count} 个
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-default-500">累计创建:</span>
                      <span className="font-medium text-primary">
                        {currentSubscription.total_created} 个
                      </span>
                    </div>

                    {/* 进度显示 */}
                    {subscriptionProgress &&
                      pullingSubscriptionId === currentSubscription.id && (
                        <div className="mt-3 space-y-2">
                          <Progress
                            color={
                              subscriptionProgress.status === "failed"
                                ? "danger"
                                : subscriptionProgress.status === "completed"
                                  ? "success"
                                  : "primary"
                            }
                            label={
                              subscriptionProgress.progress_message ||
                              "处理中..."
                            }
                            maxValue={
                              subscriptionProgress.progress_total || 100
                            }
                            showValueLabel={true}
                            size="sm"
                            value={subscriptionProgress.progress_current}
                          />
                          <div className="space-y-1">
                            <p className="text-xs text-default-500 text-center">
                              {subscriptionProgress.status === "pulling" &&
                                "正在拉取数据..."}
                              {subscriptionProgress.status === "processing" &&
                                `处理中: ${subscriptionProgress.progress_current}/${subscriptionProgress.progress_total}`}
                              {subscriptionProgress.status === "completed" &&
                                "拉取完成"}
                              {subscriptionProgress.status === "failed" &&
                                "拉取失败"}
                            </p>
                            {/* 显示错误详情 */}
                            {subscriptionProgress.status === "failed" &&
                              subscriptionProgress.error_message && (
                                <p className="text-xs text-danger text-center px-2">
                                  错误原因: {subscriptionProgress.error_message}
                                </p>
                              )}
                          </div>
                        </div>
                      )}

                    <Button
                      className="mt-2"
                      color="secondary"
                      isLoading={
                        pullingSubscriptionId === currentSubscription.id
                      }
                      isDisabled={
                        pullSubscriptionMutation.isPending ||
                        pullingSubscriptionId === currentSubscription.id
                      }
                      size="sm"
                      variant="flat"
                      onPress={() => {
                        console.log("[手动拉取] 开始拉取订阅:", currentSubscription.id);
                        pullSubscriptionMutation.mutate(currentSubscription.id);
                      }}
                    >
                      {pullingSubscriptionId === currentSubscription.id
                        ? "拉取中..."
                        : "手动拉取"}
                    </Button>
                  </div>
                </div>
              )}

              {!currentSubscription && !isLoadingSubscriptions && (
                <div className="mt-4 pt-4 border-t border-default-200">
                  <p className="text-sm text-default-500 text-center">
                    暂无订阅配置，请创建订阅
                  </p>
                </div>
              )}
            </CardBody>
          </Card>
        </div>

        {/* 扫描历史表格 */}
        <Card>
          <CardHeader>
            <p className="text-lg font-semibold">扫描历史</p>
          </CardHeader>
          <CardBody>
            {isLoading ? (
              <div className="flex flex-col gap-2 justify-center items-center h-32">
                <Progress
                  isIndeterminate
                  aria-label="加载中..."
                  className="max-w-md"
                  size="sm"
                />
                <p className="text-sm text-default-500">加载中...</p>
              </div>
            ) : (
              <Table aria-label="FOFA扫描历史表格">
                <TableHeader>
                  <TableColumn>ID</TableColumn>
                  <TableColumn>查询语句</TableColumn>
                  <TableColumn>国家</TableColumn>
                  <TableColumn>状态</TableColumn>
                  <TableColumn>发现/创建</TableColumn>
                  <TableColumn>创建时间</TableColumn>
                  <TableColumn>完成时间</TableColumn>
                  <TableColumn>错误信息</TableColumn>
                </TableHeader>
                <TableBody
                  emptyContent="暂无扫描记录"
                  items={scanHistory || []}
                >
                  {(scan) => (
                    <TableRow key={scan.id}>
                      <TableCell>{scan.id}</TableCell>
                      <TableCell
                        className="max-w-xs truncate"
                        title={scan.query}
                      >
                        {scan.query}
                      </TableCell>
                      <TableCell>{scan.country}</TableCell>
                      <TableCell>{renderStatusCell(scan)}</TableCell>
                      <TableCell>
                        {scan.total_found} / {scan.total_created}
                      </TableCell>
                      <TableCell>{renderDate(scan.created_at)}</TableCell>
                      <TableCell>{renderDate(scan.completed_at)}</TableCell>
                      <TableCell
                        className="max-w-xs truncate text-danger"
                        title={scan.error_message || ""}
                      >
                        {scan.error_message || "-"}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardBody>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default FofaScanPage;
