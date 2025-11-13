import { useEffect, useState } from "react";
import { Button } from "@heroui/button";
import { Input } from "@heroui/input";
import { Card } from "@heroui/card";
import { Switch } from "@heroui/switch";
import { addToast } from "@heroui/toast";

import { authApi, settingApi } from "@/api";
import { useAuth } from "@/contexts/AuthContext";
import DashboardLayout from "@/layouts/Main";
import ErrorDisplay from "@/components/ErrorDisplay";
import { useCustomQuery } from "@/hooks";
import { SystemSettingKey, SystemSettings } from "@/types";

const Settings = () => {
  const { isAdmin, user } = useAuth();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [
    isUpdateEndpointTaskIntervalLoading,
    setIsUpdateEndpointTaskIntervalLoading,
  ] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [success, setSuccess] = useState(false);
  const [updateEndpointTaskInterval, setUpdateEndpointTaskInterval] =
    useState(24);
  const [disableOllamaApiAuth, setDisableOllamaApiAuth] = useState(false);
  const [
    isDisableOllamaApiAuthLoading,
    setIsDisableOllamaApiAuthLoading,
  ] = useState(false);

  const { data: updateEndpointTaskIntervalData } =
    useCustomQuery<SystemSettings>(
      ["updateEndpointTaskInterval"],
      () =>
        settingApi.getSettingByKey(
          SystemSettingKey.UPDATE_ENDPOINT_TASK_INTERVAL_HOURS,
        ),
      { enabled: !!user && isAdmin, staleTime: 30000 },
    );

  const { data: disableOllamaApiAuthData } =
    useCustomQuery<SystemSettings>(
      ["disableOllamaApiAuth"],
      () =>
        settingApi.getSettingByKey(
          SystemSettingKey.DISABLE_OLLAMA_API_AUTH,
        ),
      { enabled: !!user && isAdmin, staleTime: 30000 },
    );

  useEffect(() => {
    setUpdateEndpointTaskInterval(
      Number(updateEndpointTaskIntervalData?.value),
    );
  }, [updateEndpointTaskIntervalData]);

  useEffect(() => {
    setDisableOllamaApiAuth(
      disableOllamaApiAuthData?.value?.toLowerCase() === "true",
    );
  }, [disableOllamaApiAuthData]);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccess(false);

    if (!oldPassword || !newPassword || !confirmPassword) {
      setError(new Error("请填写所有密码字段"));

      return;
    }

    if (newPassword !== confirmPassword) {
      setError(new Error("新密码与确认密码不匹配"));

      return;
    }

    try {
      setIsLoading(true);
      await authApi.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
      });
      // 清空表单
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      addToast({
        title: "密码修改成功",
        description: "请使用新密码登录",
        color: "success",
      });
    } catch {
      addToast({
        title: "密码修改失败",
        description: "请检查旧密码是否正确",
        color: "danger",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateEndpointTaskInterval = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdateEndpointTaskIntervalLoading(true);

    try {
      await settingApi.updateSetting(
        SystemSettingKey.UPDATE_ENDPOINT_TASK_INTERVAL_HOURS,
        updateEndpointTaskInterval.toString(),
      );
      addToast({
        title: "更新端点任务间隔成功",
        description: "请等待端点任务更新",
        color: "success",
      });
    } catch {
      addToast({
        title: "更新端点任务间隔失败",
        description: "请检查更新端点任务间隔是否正确",
        color: "danger",
      });
    } finally {
      setIsUpdateEndpointTaskIntervalLoading(false);
    }

    setUpdateEndpointTaskInterval(Number(updateEndpointTaskIntervalData) || 24);
  };

  const handleToggleDisableOllamaApiAuth = async (value: boolean) => {
    setIsDisableOllamaApiAuthLoading(true);
    try {
      await settingApi.updateSetting(
        SystemSettingKey.DISABLE_OLLAMA_API_AUTH,
        value ? "true" : "false",
      );
      setDisableOllamaApiAuth(value);
      addToast({
        title: value ? "已禁用 Ollama API 鉴权" : "已启用 Ollama API 鉴权",
        description: value
          ? "现在访问 Ollama API 不需要提供 token"
          : "现在访问 Ollama API 需要提供 token",
        color: "success",
      });
    } catch {
      addToast({
        title: "更新设置失败",
        description: "请重试",
        color: "danger",
      });
    } finally {
      setIsDisableOllamaApiAuthLoading(false);
    }
  };

  return (
    <DashboardLayout current_root_href="/settings">
      <div className="max-w-3xl mx-auto">
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-6">修改密码</h2>

          {error && <ErrorDisplay className="mb-4" error={error} />}

          {success && (
            <div className="p-4 mb-4 text-white bg-success-500 rounded-md">
              <p>密码修改成功！</p>
            </div>
          )}

          <form onSubmit={handleChangePassword}>
            <div className="space-y-4">
              <div>
                {/* <label
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                  htmlFor="oldPassword"
                >
                  当前密码
                </label> */}
                <Input
                  fullWidth
                  id="oldPassword"
                  label="当前密码"
                  placeholder="请输入当前密码"
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                />
              </div>

              <div>
                <Input
                  fullWidth
                  id="newPassword"
                  label="新密码"
                  placeholder="请输入新密码"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>

              <div>
                <Input
                  fullWidth
                  id="confirmPassword"
                  label="确认新密码"
                  placeholder="请再次输入新密码"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="mt-6">
              <Button color="primary" isLoading={isLoading} type="submit">
                修改密码
              </Button>
            </div>
          </form>
        </Card>

        {isAdmin && (
          <>
            <Card className="p-6 mt-6">
              <h2 className="text-xl font-semibold mb-4">系统设置</h2>
              <form onSubmit={handleUpdateEndpointTaskInterval}>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <Input
                      description="设为 0 禁用自动更新"
                      label="更新端点任务间隔（小时）"
                      min={0}
                      type="number"
                      value={updateEndpointTaskInterval}
                      onChange={(e) =>
                        setUpdateEndpointTaskInterval(Number(e.target.value))
                      }
                    />
                  </div>
                  <div className="flex justify-between">
                    <Button
                      color="primary"
                      isLoading={isUpdateEndpointTaskIntervalLoading}
                      type="submit"
                    >
                      更新
                    </Button>
                  </div>
                </div>
              </form>
            </Card>

            <Card className="p-6 mt-6">
              <h2 className="text-xl font-semibold mb-4">API 设置</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex flex-col gap-1">
                    <span className="text-base font-medium">
                      禁用 Ollama API 鉴权
                    </span>
                    <span className="text-sm text-default-500">
                      开启后，访问 Ollama API 将不需要提供 token
                    </span>
                  </div>
                  <Switch
                    isSelected={disableOllamaApiAuth}
                    isDisabled={isDisableOllamaApiAuthLoading}
                    onValueChange={handleToggleDisableOllamaApiAuth}
                    color="primary"
                  />
                </div>
              </div>
            </Card>
          </>
        )}

        <Card className="p-6 mt-6">
          <h2 className="text-xl font-semibold mb-4">账户信息</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">用户名：</span>
              <span className="font-medium">{user?.username}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">
                用户 ID：
              </span>
              <span className="font-medium">{user?.id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">
                用户类型：
              </span>
              <span className="font-medium">
                {user?.is_admin ? "管理员" : "普通用户"}
              </span>
            </div>
          </div>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default Settings;
