# -*- coding: utf-8 -*-
"""
AI Agent 工具集
供 AI agent 读取测试报告（JUnit XML / Allure 原始数据）、YAML 测试用例、日志文件，
检索报告关键字，并推送飞书通知。所有文件读写都被限制在项目目录内。
"""

import glob
import json
import os
import re
import xml.etree.ElementTree as ET

from common.perf_stats import compute_perf_stats
from common.recordlog import logs
from conf import setting

# 单个工具返回的最大字符数，避免把大响应/日志全部塞进上下文
MAX_TEXT_LEN = 20000

REPORT_DIR = os.path.join(setting.DIR_BASE, "report")
RESULTS_XML = os.path.join(REPORT_DIR, "results.xml")
ALLURE_RAW_DIR = os.path.join(REPORT_DIR, "temp")
ALLURE_HTML_DIR = os.path.join(REPORT_DIR, "allureReport")
LOG_DIR = os.path.join(setting.DIR_BASE, "logs")


def _truncate(text):
    text = str(text)
    if len(text) <= MAX_TEXT_LEN:
        return text
    return text[:MAX_TEXT_LEN] + "\n...(已截断，共 {} 字符)".format(len(text))


def _error(msg):
    return json.dumps({"error": msg}, ensure_ascii=False)


def _ensure_inside(path):
    """确保解析后的路径位于项目根目录内，防止 agent 被诱导读取任意文件。"""
    real = os.path.realpath(path)
    root = os.path.realpath(setting.DIR_BASE)
    if real != root and not real.startswith(root + os.sep):
        raise ValueError("路径必须在项目目录内: {}".format(real))
    return real


def _ai_config():
    from conf.operationConfig import OperationConfig

    try:
        return OperationConfig().get_item_value("AI")
    except Exception:
        return {}


def get_test_summary():
    """读取 report/results.xml（JUnit 格式），返回测试统计与失败/跳过/出错用例明细。"""
    if not os.path.exists(RESULTS_XML):
        return _error("未找到 {}，请先运行 python run.py 生成测试报告".format(RESULTS_XML))
    try:
        root = ET.parse(RESULTS_XML).getroot()
    except Exception as e:
        return _error("解析 results.xml 失败: {}".format(e))
    suites = root.findall("testsuite") or ([root] if root.tag == "testsuite" else [])
    summary, failed_cases = {}, []
    for suite in suites:
        for key in ("tests", "failures", "errors", "skipped", "time", "timestamp", "hostname"):
            if suite.get(key) is not None:
                summary[key] = suite.get(key)
        for tc in suite.iter("testcase"):
            status, message = "passed", ""
            for tag in ("failure", "error", "skipped"):
                node = tc.find(tag)
                if node is not None:
                    status, message = tag, (node.get("message") or node.text or "")[:2000]
                    break
            if status != "passed":
                failed_cases.append(
                    {
                        "name": tc.get("name"),
                        "classname": tc.get("classname"),
                        "time": tc.get("time"),
                        "status": status,
                        "message": message,
                    }
                )
    return _truncate(
        json.dumps(
            {"summary": summary, "failed_cases": failed_cases, "source": RESULTS_XML}, ensure_ascii=False, indent=2
        )
    )


def get_allure_metrics():
    """读取 Allure 的套件/功能分组与环境信息；统计数字以 JUnit 为准，避免重复。"""
    result = {}
    widgets = os.path.join(ALLURE_HTML_DIR, "widgets")
    for filename in ("suites.json", "behaviors.json", "environment.json"):
        path = os.path.join(widgets, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                result[filename] = json.loads(content) if content.strip() else {}
            except Exception as e:
                result[filename] = "解析失败: {}".format(e)
    return _truncate(json.dumps(result, ensure_ascii=False, indent=2))


def read_testcase_yaml(path):
    """读取指定的 YAML 测试用例文件，用于查看失败用例的请求参数与断言定义。"""
    full_path = path if os.path.isabs(path) else os.path.join(setting.DIR_BASE, path)
    try:
        full_path = _ensure_inside(full_path)
    except ValueError as e:
        return _error(str(e))
    if not os.path.exists(full_path):
        return _error("文件不存在: {}".format(full_path))
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return _truncate(f.read())
    except Exception as e:
        return _error("读取 YAML 失败: {}".format(e))


def read_case_attachments(case_name):
    """
    在 report/temp 的 Allure 原始结果中按用例名查找用例，
    返回用例状态和请求/响应等附件日志内容。
    """
    if not os.path.isdir(ALLURE_RAW_DIR):
        return _error("Allure 原始结果目录不存在: {}".format(ALLURE_RAW_DIR))
    # 从 pytest 参数化名（test_delete_user[base_info1-testcase1]）提取函数名
    func_match = re.match(r"^(test_\w+)", str(case_name))
    func_name = func_match.group(1) if func_match else None
    matched, fuzzy = [], []
    for filename in os.listdir(ALLURE_RAW_DIR):
        if not filename.endswith("-result.json"):
            continue
        try:
            with open(os.path.join(ALLURE_RAW_DIR, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        name = data.get("name") or ""
        full_name = data.get("fullName") or ""
        if name == case_name or full_name == case_name:
            matched.append(data)
        elif func_name and full_name.endswith("#" + func_name):
            fuzzy.append(data)
    candidates = matched or fuzzy
    if not candidates:
        return _error("未在 Allure 原始结果中找到用例: {}".format(case_name))
    matches = []
    for data in candidates[:3]:
        attachments = []
        for att in data.get("attachments", []):
            src = att.get("source")
            if not src:
                continue
            att_path = os.path.join(ALLURE_RAW_DIR, src)
            try:
                with open(att_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = "读取附件失败: {}".format(e)
            attachments.append({"name": att.get("name"), "content": content[:4000]})
        matches.append(
            {
                "name": data.get("name"),
                "fullName": data.get("fullName"),
                "status": data.get("status"),
                "feature": [lb.get("value") for lb in data.get("labels", []) if lb.get("name") == "feature"],
                "story": [lb.get("value") for lb in data.get("labels", []) if lb.get("name") == "story"],
                "attachments": attachments,
            }
        )
    return _truncate(json.dumps({"case_name": case_name, "matches": matches}, ensure_ascii=False, indent=2))


def read_log_file(path=None, lines=200):
    """读取日志文件末尾内容；path 缺省时读取 report/logs/ 下最新的测试日志。"""
    full_path = path
    if not full_path:
        if not os.path.isdir(LOG_DIR):
            return _error("日志目录不存在: {}".format(LOG_DIR))
        candidates = sorted(glob.glob(os.path.join(LOG_DIR, "*.logs")), key=os.path.getmtime, reverse=True)
        if not candidates:
            return _error("report/logs/ 目录下没有日志文件")
        full_path = candidates[0]
    elif not os.path.isabs(full_path):
        full_path = os.path.join(setting.DIR_BASE, full_path)
    try:
        full_path = _ensure_inside(full_path)
    except ValueError as e:
        return _error(str(e))
    if not os.path.exists(full_path):
        return _error("日志文件不存在: {}".format(full_path))
    try:
        lines = max(1, min(int(lines), 5000))
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            data = f.readlines()
        content = "".join(data[-lines:]) or "（日志文件为空）"
        return _truncate("日志文件: {}\n{}".format(full_path, content))
    except Exception as e:
        return _error("读取日志失败: {}".format(e))


def search_in_report(keyword, directory="report/temp"):
    """在报告/日志目录中检索关键字，返回匹配的文件路径、行号和内容片段。"""
    base = os.path.join(setting.DIR_BASE, directory)
    try:
        base = _ensure_inside(base)
    except ValueError as e:
        return _error(str(e))
    if not os.path.isdir(base):
        return _error("目录不存在: {}".format(base))
    matches = []
    for root_dir, _, files in os.walk(base):
        for name in files:
            if not name.endswith((".txt", ".json", ".xml", ".logs", ".yaml", ".yml")):
                continue
            path = os.path.join(root_dir, name)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    for line_no, line in enumerate(f, 1):
                        if keyword in line:
                            matches.append(
                                {
                                    "file": os.path.relpath(path, setting.DIR_BASE),
                                    "line": line_no,
                                    "snippet": line.strip()[:300],
                                }
                            )
                            if len(matches) >= 30:
                                return _truncate(
                                    json.dumps({"keyword": keyword, "matches": matches}, ensure_ascii=False, indent=2)
                                )
            except Exception:
                continue
    return _truncate(json.dumps({"keyword": keyword, "matches": matches}, ensure_ascii=False, indent=2))


def send_feishu(content):
    """将内容推送到飞书机器人；webhook 来自 [AI] feishu_webhook。"""
    from common.feishuRobot import send_feishu_msg

    return "飞书推送结果: {}".format(send_feishu_msg(content))


def get_perf_stats():
    """读取 report/results.xml 计算用例执行耗时分布（P50/P90/P95/P99）。"""
    return json.dumps(compute_perf_stats(), ensure_ascii=False, indent=2)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_test_summary",
            "description": "读取 report/results.xml（JUnit 格式），返回本次测试的统计信息以及失败/跳过/出错用例明细（含失败信息）。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_allure_metrics",
            "description": "读取 Allure 报告的套件/功能分组与环境信息，用于了解用例所属模块分布（统计数字以 JUnit 的 get_test_summary 为准）。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_testcase_yaml",
            "description": "读取指定 YAML 测试用例文件的内容，用于查看失败用例的接口地址、请求参数和断言定义。路径相对项目根目录，例如 testcase/ProductManager/getProductList.yaml。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "YAML 文件路径（相对项目根目录）"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_case_attachments",
            "description": "在 Allure 原始结果中按用例名称查找用例，返回其请求/响应等附件日志内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "用例名称，如 test_delete_user[base_info1-testcase1]",
                    }
                },
                "required": ["case_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_log_file",
            "description": "读取日志文件末尾内容。path 缺省时读取 report/logs/ 目录下最新的测试日志。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "日志文件路径（相对项目根目录），可省略"},
                    "lines": {"type": "integer", "description": "读取末尾行数，默认 200"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_report",
            "description": "在报告或日志目录中检索关键字（如 error_code、断言失败），返回匹配的文件路径、行号和内容片段。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "要检索的关键字"},
                    "directory": {"type": "string", "description": "检索目录（相对项目根目录），默认 report/temp"},
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_feishu",
            "description": "将分析结果推送到飞书机器人，适用于需要人工关注的失败或异常情况。",
            "parameters": {
                "type": "object",
                "properties": {"content": {"type": "string", "description": "要推送的文本内容"}},
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_perf_stats",
            "description": "读取 report/results.xml 计算本次测试的用例耗时分布（P50/P90/P95/P99、均值、总耗时）。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

TOOL_FUNCTIONS = {
    "get_test_summary": get_test_summary,
    "get_allure_metrics": get_allure_metrics,
    "read_testcase_yaml": read_testcase_yaml,
    "read_case_attachments": read_case_attachments,
    "read_log_file": read_log_file,
    "search_in_report": search_in_report,
    "send_feishu": send_feishu,
    "get_perf_stats": get_perf_stats,
}


def execute_tool(name, args=None):
    """执行工具并返回字符串结果（供 agent loop 调用）。"""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return json.dumps(
            {"error": "未知工具: {}，可选工具: {}".format(name, ", ".join(TOOL_FUNCTIONS))}, ensure_ascii=False
        )
    try:
        if args is None:
            args = {}
        elif isinstance(args, str):
            args = json.loads(args) if args.strip() else {}
        if not isinstance(args, dict):
            return json.dumps({"error": "工具参数必须是对象: {}".format(name)}, ensure_ascii=False)
        return func(**args)
    except TypeError as e:
        return json.dumps({"error": "工具参数错误 {}: {}".format(name, e)}, ensure_ascii=False)
    except Exception as e:
        logs.error("工具 {} 执行异常: {}".format(name, e))
        return json.dumps({"error": "工具 {} 执行异常: {}".format(name, e)}, ensure_ascii=False)
