import React, { useState } from "react";
import { Button } from "@heroui/button";
import { Input } from "@heroui/input";
import { Textarea } from "@heroui/input";
import { Tabs, Tab } from "@heroui/tabs";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from "@heroui/modal";
import { addToast } from "@heroui/toast";
import { Form } from "@heroui/form";

import { endpointApi } from "@/api";
import { EndpointCreate } from "@/types";

interface CreateEndpointModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const CreateEndpointModal: React.FC<CreateEndpointModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [selectedTab, setSelectedTab] = useState("single");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 创建端点表单状态
  const [formData, setFormData] = useState<EndpointCreate>({
    url: "",
    name: "",
  });

  // 批量创建端点表单状态
  const [urls, setUrls] = useState("");

  // 处理表单输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  // 处理批量创建文本区域变化
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setUrls(e.target.value);
  };

  // 处理创建端点表单提交
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // 表单验证
      if (!formData.url) {
        throw new Error("URL 不能为空");
      }

      // 确保 URL 格式正确
      let url = formData.url;

      if (!url.startsWith("http://") && !url.startsWith("https://")) {
        url = `http://${url}`;
      }

      // 如果名称为空，使用 URL 作为名称
      let name = formData.name;

      if (!name) {
        name = new URL(url).hostname;
      }

      // 提交创建请求
      await endpointApi.createEndpoint({
        url,
        name,
      });

      // 创建成功，关闭模态框并刷新列表
      handleClose();
      onSuccess();

      // 重置表单
      setFormData({
        url: "",
        name: "",
      });
      setSelectedTab("single");
    } catch (err) {
      addToast({
        title: "创建端点失败",
        description: (err as Error)?.message || "请重试",
        color: "danger",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // 处理批量创建表单提交
  const handleBatchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // 分割 URL 并过滤空行，然后去重
      const urlLines = Array.from(
        new Set(
          urls
            .split("\n")
            .map((line) => line.trim())
            .filter((line) => line)
        )
      );

      if (urlLines.length === 0) {
        throw new Error("请输入至少一个有效的端点 URL");
      }

      // 处理批量创建，先处理 URL 格式，然后去重
      const processedEndpoints: EndpointCreate[] = urlLines.map((url) => {
        // 确保 URL 格式正确
        let processedUrl = url;

        if (!url.startsWith("http://") && !url.startsWith("https://")) {
          processedUrl = `http://${url}`;
        }

        // 自动生成名称
        let name: string;

        try {
          name = new URL(processedUrl).hostname;
        } catch {
          name = processedUrl;
        }

        return {
          url: processedUrl,
          name: name,
        };
      });

      // 按 URL 去重（处理后的 URL 可能重复）
      const uniqueEndpointsMap = new Map<string, EndpointCreate>();
      processedEndpoints.forEach((ep) => {
        if (!uniqueEndpointsMap.has(ep.url)) {
          uniqueEndpointsMap.set(ep.url, ep);
        }
      });
      const endpoints = Array.from(uniqueEndpointsMap.values());

      // 提交批量创建请求
      await endpointApi.batchCreateEndpoints({
        endpoints,
      });

      // 设置成功消息并清空表单
      addToast({
        title: `批量创建端点请求已提交`,
        description: `已处理 ${endpoints.length} 个唯一端点（后端会自动跳过已存在的端点）`,
        color: "success",
        duration: 4000,
      });
      setUrls("");
      handleClose();
      onSuccess();
    } catch (err) {
      addToast({
        title: "批量创建端点失败",
        description: (err as Error)?.message || "请重试",
        color: "danger",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // 关闭模态框并重置表单
  const handleClose = () => {
    if (!isSubmitting) {
      onClose();
      setSelectedTab("single");
      setFormData({
        url: "",
        name: "",
      });
      setUrls("");
    }
  };

  return (
    <Modal isOpen={isOpen} placement="center" onClose={handleClose}>
      <ModalContent>
        {() => (
          <Form
            className="w-full"
            id="create-endpoint-form"
            onSubmit={
              selectedTab === "single" ? handleCreateSubmit : handleBatchSubmit
            }
          >
            <ModalHeader>创建新端点</ModalHeader>
            <ModalBody className="w-full">
              <Tabs
                classNames={{
                  tabList: "mb-4",
                }}
                selectedKey={selectedTab}
                onSelectionChange={setSelectedTab as (key: string) => void}
              >
                <Tab key="single" title="单个创建">
                  <div className="space-y-4">
                    <div className="mb-4">
                      <Input
                        isRequired
                        className="w-full"
                        description="输入 Ollama 服务的完整 URL，包括协议和端口"
                        id="url"
                        label="端点 URL"
                        name="url"
                        placeholder="例如: http://localhost:11434"
                        value={formData.url}
                        onChange={handleInputChange}
                      />
                    </div>

                    <div className="mb-6">
                      <Input
                        className="w-full"
                        description="可选，如不填写将使用 URL 主机名"
                        id="name"
                        label="端点名称"
                        name="name"
                        placeholder="给端点起个名字"
                        value={formData.name}
                        onChange={handleInputChange}
                      />
                    </div>
                  </div>
                </Tab>
                <Tab key="batch" title="批量创建">
                  <div className="mb-6">
                    <Textarea
                      isRequired
                      className="w-full min-h-[200px]"
                      description="每行输入一个 URL。如果没有指定协议，将默认使用 http://。系统会自动以主机名作为端点名称。"
                      id="urls"
                      label="端点 URLs"
                      placeholder={`每行输入一个 URL，例如: \nhttp://localhost:11434 \n192.168.1.100:11434 \nollama-server-2:11434`}
                      value={urls}
                      onChange={handleTextChange}
                    />
                  </div>
                </Tab>
              </Tabs>
            </ModalBody>
            <ModalFooter className="w-full">
              <Button
                disabled={isSubmitting}
                variant="light"
                onPress={handleClose}
              >
                取消
              </Button>
              {selectedTab === "single" ? (
                <Button
                  color="primary"
                  disabled={isSubmitting}
                  isLoading={isSubmitting}
                  type="submit"
                >
                  创建
                </Button>
              ) : (
                <Button
                  color="primary"
                  disabled={isSubmitting}
                  isLoading={isSubmitting}
                  type="submit"
                >
                  {isSubmitting ? (
                    <>
                      <span className="ml-2">创建中...</span>
                    </>
                  ) : (
                    "批量创建"
                  )}
                </Button>
              )}
            </ModalFooter>
          </Form>
        )}
      </ModalContent>
    </Modal>
  );
};

export default CreateEndpointModal;
