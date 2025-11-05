import asyncio
from typing import List, Optional

from pydantic import BaseModel

from src.ai_model.models import AIModelDB, AIModelPerformanceDB, AIModelStatusEnum
from src.endpoint.models import EndpointDB, EndpointPerformanceDB, EndpointStatusEnum
from src.endpoint.utils import get_token_count
from src.logging import get_logger
from src.ollama.client import OllamaClient
from src.ollama.fake_detector import FakeOllamaDetector

logger = get_logger(__name__)

# 测试提示词列表（对齐AOS + 保留中文）
# 对应 AOS: ollama-utils.ts:10-14
DEFAULT_TEST_PROMPTS = [
    "将以下内容，翻译成现代汉语：先帝创业未半而中道崩殂，今天下三分，益州疲弊，此诚危急存亡之秋也。",
    "解释递归算法的基本原理，并给出一个简单的例子。",
    "量子计算和经典计算的主要区别是什么？请简要说明。",
]


class ModelPerformance(BaseModel):
    ai_model: AIModelDB
    performance: AIModelPerformanceDB


class EndpointTestResult(BaseModel):
    endpoint_performance: Optional[EndpointPerformanceDB] = None
    model_performances: List[ModelPerformance] = []


async def get_ai_models(
    ollama_client: OllamaClient,
) -> List[AIModelDB]:
    """
    Get the list of models from the endpoint.
    """
    result = []
    try:
        models_raw = await ollama_client.tags()
        for model_raw in models_raw.models:
            name, tag = model_raw.model.split(":", 1)
            model = AIModelDB(
                name=name,
                tag=tag,
            )
            result.append(model)
            logger.debug(f"Model: {model.name}, Tag: {model.tag}, Size: {model_raw.size}")
        return result
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return result


async def test_ai_model_multi_round(
    ollama_client: OllamaClient,
    ai_model: AIModelDB,
    prompts: Optional[List[str]] = None,
    rounds: int = 3,
    interval: float = 1.0,
    timeout: int = 60,
) -> AIModelPerformanceDB:
    """
    多轮测试AI模型性能（对齐AOS实现）
    
    对应 AOS: detect.ts:18-97 measureTPS()
    核心逻辑:
    1. 多轮循环测试（默认3轮）
    2. 每轮使用不同的提示词
    3. 实时伪装检测（关键词 + TPS）
    4. 计算平均TPS
    5. 间隔控制（1秒）
    
    Args:
        ollama_client: Ollama客户端
        ai_model: 模型信息
        prompts: 测试提示词列表（默认使用DEFAULT_TEST_PROMPTS）
        rounds: 测试轮数（默认3轮，对齐AOS）
        interval: 轮次间隔秒数（默认1秒，对齐AOS）
        timeout: 单轮超时时间
        
    Returns:
        AIModelPerformanceDB: 性能测试结果
    """
    if prompts is None:
        prompts = DEFAULT_TEST_PROMPTS

    try:
        total_tokens = 0
        total_time = 0
        outputs = []
        first_connection_time = 0

        logger.debug(
            f"开始多轮测试: {ai_model.name}:{ai_model.tag}, "
            f"轮数: {rounds}, 间隔: {interval}s"
        )

        # 多轮测试循环（对齐AOS: detect.ts:26-76）
        for round_idx in range(rounds):
            prompt = prompts[round_idx % len(prompts)]
            logger.debug(f"第 {round_idx + 1}/{rounds} 轮测试, 提示词长度: {len(prompt)}")

            output = ""
            output_tokens = 0
            connection_time = 0
            response = None

            try:
                async with asyncio.timeout(timeout):
                    start_time = asyncio.get_event_loop().time()
                    async for response in await ollama_client.generate(
                        model=f"{ai_model.name}:{ai_model.tag}",
                        prompt=prompt,
                        stream=True,
                    ):
                        if not connection_time:
                            connection_time = asyncio.get_event_loop().time() - start_time
                            if round_idx == 0:
                                first_connection_time = connection_time

                        output += response.response

                        # 实时伪装检测（对齐AOS: detect.ts:45-48）
                        if FakeOllamaDetector.is_fake_response(output):
                            logger.warning(
                                f"第 {round_idx + 1} 轮检测到伪装服务: "
                                f"{ai_model.name}:{ai_model.tag}"
                            )
                            return AIModelPerformanceDB(status=AIModelStatusEnum.FAKE)

                        if response.done:
                            break

            except asyncio.TimeoutError:
                logger.debug(f"第 {round_idx + 1} 轮测试超时: {timeout} 秒")
                continue
            except Exception as e:
                logger.debug(f"第 {round_idx + 1} 轮测试错误: {e}")
                continue

            if not response or not response.done:
                logger.debug(f"第 {round_idx + 1} 轮未获得完整响应")
                continue

            end_time = asyncio.get_event_loop().time()

            # 获取token数量（对齐AOS: detect.ts:52,62-63）
            if response.eval_count:
                output_tokens = response.eval_count
            else:
                output_tokens = get_token_count(output)

            round_time = end_time - start_time

            # 累计统计（对齐AOS: detect.ts:62-63）
            total_tokens += output_tokens
            total_time += round_time
            outputs.append(output)

            # 计算当前轮次TPS并验证（对齐AOS: detect.ts:53-60）
            if round_time > 0:
                round_tps = output_tokens / round_time
                if not FakeOllamaDetector.is_valid_tps(round_tps):
                    logger.debug(
                        f"第 {round_idx + 1} 轮检测到异常TPS: {round_tps:.2f}, "
                        f"继续收集数据"
                    )

            logger.debug(
                f"第 {round_idx + 1} 轮完成: "
                f"{output_tokens} tokens, {round_time:.2f}s, "
                f"TPS: {output_tokens/round_time:.2f}"
            )

            # 间隔控制（对齐AOS: detect.ts:75）
            if round_idx < rounds - 1:
                await asyncio.sleep(interval)

        # 检查是否至少完成一轮测试
        if total_tokens == 0 or total_time == 0:
            logger.debug(f"所有轮次测试失败: {ai_model.name}:{ai_model.tag}")
            return AIModelPerformanceDB(status=AIModelStatusEnum.UNAVAILABLE)

        # 计算平均TPS（对齐AOS: detect.ts:84）
        avg_tps = total_tokens / total_time

        # 最终TPS合理性验证（对齐AOS: detect.ts:87-90）
        is_fake, reason = FakeOllamaDetector.detect("", avg_tps)
        if is_fake:
            logger.warning(
                f"最终检测为伪装服务: {ai_model.name}:{ai_model.tag}, "
                f"原因: {reason}"
            )
            return AIModelPerformanceDB(
                status=AIModelStatusEnum.FAKE,
                token_per_second=avg_tps,
                output=f"伪装检测: {reason}",
            )

        # 返回成功结果
        avg_time_per_round = total_time / rounds
        avg_tokens_per_round = total_tokens // rounds

        logger.info(
            f"多轮测试完成: {ai_model.name}:{ai_model.tag}, "
            f"平均TPS: {avg_tps:.2f}, "
            f"总tokens: {total_tokens}, 总时间: {total_time:.2f}s"
        )

        return AIModelPerformanceDB(
            status=AIModelStatusEnum.AVAILABLE,
            token_per_second=avg_tps,
            connection_time=first_connection_time,
            total_time=avg_time_per_round,
            output=outputs[0] if outputs else "",  # 只保存第一轮输出
            output_tokens=avg_tokens_per_round,
        )

    except Exception as e:
        logger.error(f"多轮测试异常: {ai_model.name}:{ai_model.tag}, 错误: {e}")
        return AIModelPerformanceDB(status=AIModelStatusEnum.UNAVAILABLE)


async def test_ai_model(
    ollama_client: OllamaClient,
    ai_model: AIModelDB,
    prompt: str = "将以下内容，翻译成现代汉语：先帝创业未半而中道崩殂，今天下三分，益州疲弊，此诚危急存亡之秋也。",
    timeout: int = 60,
    enable_multi_round: bool = True,
) -> AIModelPerformanceDB:
    """
    测试AI模型性能
    
    增强功能:
    - 默认启用多轮测试（enable_multi_round=True）
    - 支持切换单轮/多轮模式（向后兼容）
    
    Args:
        ollama_client: Ollama客户端
        ai_model: 模型信息
        prompt: 单轮测试提示词（当enable_multi_round=False时使用）
        timeout: 超时时间（秒）
        enable_multi_round: 是否启用多轮测试（默认True）
        
    Returns:
        AIModelPerformanceDB: 性能测试结果
    """
    # 优先使用多轮测试（对齐AOS默认行为）
    if enable_multi_round:
        return await test_ai_model_multi_round(
            ollama_client=ollama_client,
            ai_model=ai_model,
            timeout=timeout,
        )

    # 单轮测试（保留原有逻辑，向后兼容）
    try:
        output = ""
        output_tokens = 0
        connection_time = 0
        total_time = 0
        token_per_second = 0
        response = None
        try:
            async with asyncio.timeout(timeout):
                start_time = asyncio.get_event_loop().time()
                async for response in await ollama_client.generate(
                    model=f"{ai_model.name}:{ai_model.tag}",
                    prompt=prompt,
                    stream=True,
                ):
                    if not connection_time:
                        connection_time = asyncio.get_event_loop().time() - start_time
                        logger.debug(
                            f"Connection time: {connection_time}, "
                            f"Model: {ai_model.name}:{ai_model.tag}"
                        )
                    output += response.response
                    # 使用增强的伪装检测器
                    if FakeOllamaDetector.is_fake_response(output):
                        logger.error(f"Fake endpoint detected: {ai_model.name}:{ai_model.tag}")
                        return AIModelPerformanceDB(
                            status=AIModelStatusEnum.FAKE,
                        )
                    if response.done:
                        break
        except asyncio.TimeoutError:
            logger.debug(f"Timeout error: {timeout} seconds")
        except Exception as e:
            logger.debug(f"Error testing model {ai_model.name}:{ai_model.tag}: {e}")

        if not response:
            logger.debug(f"No response from model {ai_model.name}:{ai_model.tag}")
            raise Exception("No response from model")

        logger.debug(f"Response: {output}, " f"Model: {ai_model.name}:{ai_model.tag}")
        end_time = asyncio.get_event_loop().time()
        if response.done and response.eval_count:
            output_tokens = response.eval_count
        else:
            output_tokens = get_token_count(output)

        total_time = end_time - start_time
        token_per_second = output_tokens / total_time
        # token_per_second = output_tokens / (total_time - connection_time)
        performance = AIModelPerformanceDB(
            status=AIModelStatusEnum.AVAILABLE,
            token_per_second=token_per_second,
            connection_time=connection_time,
            total_time=total_time,
            output=output,
            output_tokens=output_tokens,
        )
        return performance
    except Exception as e:
        logger.debug(f"Error testing model {ai_model.name}:{ai_model.tag}: {e}")
        return AIModelPerformanceDB(
            status=AIModelStatusEnum.UNAVAILABLE,
        )


async def test_endpoint(
    endpoint: EndpointDB,
) -> EndpointTestResult:
    """
    Test the endpoint by checking its availability and testing each AI model.
    """
    test_reuslt = EndpointTestResult()
    async with OllamaClient(endpoint.url).connect() as ollama_client:
        try:
            version = await ollama_client.version()
            test_reuslt.endpoint_performance = EndpointPerformanceDB(
                status=EndpointStatusEnum.AVAILABLE,
                ollama_version=version.version,
            )
            logger.info(f"Endpoint version: {version.version}")
        except Exception as e:
            logger.debug(f"Error checking endpoint {endpoint.name}: {e}")
            test_reuslt.endpoint_performance = EndpointPerformanceDB(
                status=EndpointStatusEnum.UNAVAILABLE,
            )
            return test_reuslt

        ai_models = await get_ai_models(ollama_client)

        for ai_model in ai_models:
            if test_reuslt.endpoint_performance.status == EndpointStatusEnum.FAKE:
                model_performance = ModelPerformance(
                    ai_model=ai_model,
                    performance=AIModelPerformanceDB(
                        status=AIModelStatusEnum.FAKE,
                    ),
                )
                test_reuslt.model_performances.append(model_performance)
                logger.debug(
                    f"Fake endpoint {endpoint.name}, skipping model {ai_model.name}:{ai_model.tag}"
                )
                continue

            performance = await test_ai_model(ollama_client, ai_model)
            match performance.status:
                case AIModelStatusEnum.AVAILABLE:
                    logger.info(
                        f"Performance: {performance.token_per_second:.2f} tps "
                        f"({performance.output_tokens} tokens in {performance.total_time:.2f} s), "
                        f"Model: {ai_model.name}:{ai_model.tag} @ "
                        f"{endpoint.name},"
                    )
                case AIModelStatusEnum.UNAVAILABLE:
                    logger.debug(f"Model {ai_model.name}:{ai_model.tag} is not available, skipping")
                case AIModelStatusEnum.FAKE:
                    logger.debug(f"Fake endpoint detected: {endpoint.name}")
                    # set endpoint status to fake
                    test_reuslt.endpoint_performance = EndpointPerformanceDB(
                        status=EndpointStatusEnum.FAKE,
                    )
                case _:
                    logger.debug(f"Model {ai_model.name}:{ai_model.tag} is not available, skipping")

            model_performance = ModelPerformance(ai_model=ai_model, performance=performance)
            test_reuslt.model_performances.append(model_performance)

        return test_reuslt


if __name__ == "__main__":
    import os

    async def main():
        endpoint = EndpointDB(
            url=os.getenv("ENDPOINT", "http://localhost:11434"),
            name=os.getenv("ENDPOINT_NAME", "ollama"),
        )

        test_result = await test_endpoint(endpoint)
        logger.info(f"Test result: {test_result.model_dump_json(indent=2)}")

    asyncio.run(main())
