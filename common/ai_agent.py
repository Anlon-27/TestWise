# -*- coding: utf-8 -*-
"""
AI Agent：自动解读测试结果的小 agent

流程：
1. 读取 conf/config.ini 的 [AI] 配置；
2. 向 LLM 发起对话，LLM 按需调用工具（读取 JUnit/Allure 报告、YAML 用例、日志等）；
3. 循环执行工具并把结果回传给 LLM，直到 LLM 输出最终分析；
4. 最终分析打印到控制台；LLM 可主动调用 send_feishu 推送通知。

用法：
- 测试结束后自动分析：conf/config.ini [AI] enable=true，再运行 python run.py
- 只分析已有报告：python run.py --analyze
"""

import json
import os
import re

import requests

from common import ai_tools
from common.recordlog import logs
from conf.operationConfig import OperationConfig

SYSTEM_PROMPT = """你是这个 Pytest 自动化测试框架的结果分析助手。

框架特点：
- 测试用例由 Python 文件 + YAML 数据组成，YAML 里包含接口地址、请求参数、断言（validation）和参数提取（extract_list）；
- 运行入口 python run.py，报告生成在 report/ 下：JUnit 格式 report/results.xml、Allure 原始结果 report/temp/；
- 断言支持 contains / eq / ne / rv / db；常见失败原因：断言值与实际响应不匹配、参数过期、依赖接口失败、mock 服务未启动等。

你的任务：分析最近一次测试运行结果，输出简洁的中文分析报告，包括：
1. 总体结论（通过/失败数量、耗时、环境信息）；
2. 失败用例明细与根因分析（区分代码问题/数据问题/环境问题/断言问题）；
3. 针对每个失败的修复建议（可引用 YAML 文件路径和字段）；
4. 需要人工关注的提示。

工作方式：按需调用工具获取信息，分析完成后再给出最终报告；不要编造未读取到的数据。
"""

JSON_PROMPT_SUFFIX = """

【重要】当前接口不支持原生工具调用，请改用 JSON 协议：
- 需要调用工具时，只输出一个 JSON 对象：{"tool": "<工具名>", "args": {...}}
- 分析完成时，只输出：{"final": "<完整分析报告>"}
不要输出 JSON 以外的任何内容。
"""


class LLMClient:
    """OpenAI 兼容的 Chat Completions 客户端（OpenAI/DeepSeek/Qwen/Ollama 等）。"""

    def __init__(self, base_url, api_key, model, temperature=0.2):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.model = model
        self.temperature = temperature
        # 原生工具调用不可用时会自动切换为 JSON 协议
        self.json_mode = False

    def chat(self, messages, tools=None):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools and not self.json_mode:
            payload["tools"] = tools
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer {}".format(self.api_key)
        try:
            resp = requests.post(
                "{}/chat/completions".format(self.base_url), json=payload, headers=headers, timeout=180
            )
        except requests.RequestException as e:
            raise RuntimeError("请求 LLM 接口失败: {}".format(e))
        if resp.status_code >= 400:
            raise RuntimeError("LLM 接口返回 {}: {}".format(resp.status_code, resp.text[:500]))
        try:
            return resp.json()["choices"][0]["message"]
        except (KeyError, ValueError) as e:
            raise RuntimeError("LLM 响应格式异常: {}".format(e))


class AgentLoop:
    """最小 agent loop：LLM 生成 -> 工具执行 -> 结果回填 -> 直到最终回答。"""

    def __init__(self, client, max_iterations=8):
        self.client = client
        self.max_iterations = max_iterations
        self.used_tools = []

    def run(self, objective):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": objective},
        ]
        for _ in range(self.max_iterations):
            try:
                message = self.client.chat(messages, tools=ai_tools.TOOLS)
            except RuntimeError as e:
                if not self.client.json_mode:
                    logs.warning("原生工具调用不可用，切换 JSON 协议: %s", e)
                    self.client.json_mode = True
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT + JSON_PROMPT_SUFFIX},
                        {"role": "user", "content": objective},
                    ]
                    continue
                raise

            content = (message.get("content") or "").strip()
            if self.client.json_mode:
                final = self._handle_json_message(messages, content)
                if final is not None:
                    return final
                continue

            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls,
                    }
                )
                for call in tool_calls[:5]:
                    function = call.get("function", {})
                    name = function.get("name", "")
                    result = ai_tools.execute_tool(name, function.get("arguments"))
                    self.used_tools.append(name)
                    logs.info("[agent] 调用工具 %s -> %s", name, result[:200])
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id", "call_{}".format(len(self.used_tools))),
                            "content": result,
                        }
                    )
                continue

            if content:
                return content
            break
        return "达到最大迭代次数（{} 轮），未能生成最终分析。".format(self.max_iterations)

    def _handle_json_message(self, messages, content):
        """JSON 协议消息：{"tool": ..., "args": ...} 或 {"final": ...}"""
        obj = self._parse_json(content)
        if isinstance(obj, dict) and obj.get("final"):
            return str(obj["final"])
        if isinstance(obj, dict) and obj.get("tool"):
            name = str(obj["tool"])
            result = ai_tools.execute_tool(name, obj.get("args") or {})
            self.used_tools.append(name)
            logs.info("[agent] 调用工具 %s -> %s", name, result[:200])
            messages.append({"role": "user", "content": "工具 {} 返回:\n{}".format(name, result)})
            return None
        messages.append({"role": "user", "content": "无法解析你的回复，请严格按 JSON 协议输出。"})
        return None

    @staticmethod
    def _parse_json(text):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
        try:
            return json.loads(text)
        except Exception:
            return None


def analyze_test_result():
    """运行 AI agent 分析最近一次测试结果；未启用或未配置时返回 None。"""
    try:
        conf = OperationConfig().get_item_value("AI")
    except Exception:
        logs.error("读取 [AI] 配置失败，请检查 conf/config.ini")
        return None

    if str(conf.get("enable", "false")).strip().lower() not in ("true", "1", "yes"):
        logs.info("AI 结果解读未启用（conf/config.ini [AI] enable=false），跳过")
        return None

    api_key = (conf.get("api_key") or "").strip() or os.environ.get("AI_API_KEY", "")
    base_url = (conf.get("base_url") or "https://api.openai.com/v1").strip()
    model = (conf.get("model") or "gpt-4o-mini").strip()
    try:
        max_iterations = int(conf.get("max_iterations") or 8)
    except (TypeError, ValueError):
        max_iterations = 8

    if not api_key:
        logs.error("未配置 API Key：请在 conf/config.ini [AI] api_key 中填写，或设置环境变量 AI_API_KEY")
        return None

    logs.info("AI 结果解读启动: model=%s, base_url=%s, max_iterations=%s", model, base_url, max_iterations)
    client = LLMClient(base_url=base_url, api_key=api_key, model=model)
    agent = AgentLoop(client=client, max_iterations=max_iterations)
    objective = (
        "请分析项目最近一次测试运行结果。请先调用工具获取测试统计和失败用例信息，"
        "必要时查看失败用例的 YAML 定义、Allure 附件日志或项目日志，"
        "然后给出中文分析报告。如果有失败用例，调用 send_feishu 推送简要结论。"
    )
    final = agent.run(objective)
    print("\n===== AI 测试结果分析 =====\n{}\n===========================".format(final))
    try:
        from common.ai_report import render_analysis_html

        out_path = render_analysis_html(
            final,
            extra={
                "tools_used": agent.used_tools,
                "model": client.model,
            },
        )
        logs.info("AI 分析报告已生成: %s", out_path)
        print("\nAI 分析报告已生成: {}".format(out_path))
    except Exception as e:
        logs.error("生成 AI 分析报告 HTML 失败: %s", e)
    return final


if __name__ == "__main__":
    analyze_test_result()
