# TestWise 智能接口测试框架

**基于 AI 驱动的接口自动化测试框架** *从用例设计到根因分析，重塑接口测试体验*

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/) [![Pytest](https://img.shields.io/badge/Pytest-8-green.svg)](https://docs.pytest.org/) [![Allure](https://img.shields.io/badge/Allure-Report-orange.svg)](https://allurereport.org/) [![AI](https://img.shields.io/badge/AI-DeepSeek-purple.svg)](https://www.deepseek.com/) [![License](https://img.shields.io/badge/License-GPL_v3-blue.svg)](LICENSE)

## 📖 项目简介

TestWise 是一个基于 Pytest 的智能接口自动化测试框架，采用 **YAML 数据驱动** 设计，集成了 **Mock 服务**、**并行执行**、**覆盖率统计** 与 **AI 结果分析** 能力，实现测试用例设计、执行、报告与根因分析的统一闭环。

---

## 🎯 核心功能

### ⚙️ YAML 数据驱动接口自动化
> **解决痛点**：传统接口测试脚本与数据耦合，用例维护成本高。
- 用例由 YAML 声明接口地址、请求参数与断言，零代码编写
- 支持参数化用例与单接口 / 业务链路场景
- 参数提取与跨用例传递（extract 机制）

### 🧪 多类型断言体系
- 支持 contains / eq / ne / rv / db / schema 六种断言模式
- 覆盖文本包含、相等校验、数据库校验与响应结构契约校验

### 🖥️ Flask Mock 服务
- 本地可离线执行，不依赖真实环境
- 支持登录、用户管理、商品下单等业务接口模拟
- 并发数据隔离改造：Token 集合校验、订单列表存储

### ⚡ 并行执行与数据隔离
- pytest-xdist 多进程并行执行，测试变量按 worker 隔离
- 失败自动重试，区分网络抖动与真实缺陷
- 测试数据自动备份与恢复，保障用例可重复执行

### 📊 覆盖率与持续集成
- pytest-cov 覆盖率统计，输出 HTML 报告
- 需求-用例映射文档，覆盖缺口可追溯
- Jenkins 定时执行与报告归档

### 🤖 AI 结果分析 Agent
> **解决痛点**：失败用例人工翻日志定位根因，效率低。
- 基于 DeepSeek 工具调用循环，自主读取 JUnit / Allure / 日志
- 输出结构化根因分析与美化 HTML 报告
- 附带 P50/P90/P95/P99 响应性能统计
- 失败自动推送飞书通知

### 🚀 性能压测与契约校验
- Locust 接口性能压测脚本
- 响应结构 schema 契约断言

---

## 🏗️ 技术架构

### 测试框架
- **语言**: Python 3.12+
- **框架**: Pytest 8 + allure-pytest + pytest-xdist + pytest-rerunfailures + pytest-cov
- **请求**: requests；**数据驱动**: PyYAML；**依赖管理**: uv

### Mock 服务
- **框架**: Flask（threaded，支持并行测试的并发请求）

### AI 集成
- **模型**: DeepSeek Chat（OpenAI 兼容接口）
- **Agent**: 自研工具调用循环（原生 function calling，自动降级 JSON 协议）
- **报告**: 自研 Markdown → HTML 渲染

### 持续集成
- Jenkins / GitHub Actions 双流水线

---

## 📁 项目结构

```text
├── base/            # 框架核心：RequestBase 引擎、请求发送
├── common/          # 公共模块：断言、数据工厂、性能统计、AI Agent
├── conf/            # 配置：setting.py / config.ini
├── testcase/        # 测试用例（Python + YAML，按业务模块分组）
├── data/            # 测试数据
├── mock_server/     # Flask Mock 服务
├── perf/            # Locust 性能压测
├── docs/            # 需求-用例映射等文档
├── report/          # 所有生成物统一存放：报告 / 日志 / 覆盖率
├── .github/         # GitHub Actions 流水线
└── Jenkinsfile      # Jenkins 流水线
```

---

## 🚀 快速开始

### 环境要求
- **Python**: 3.12+
- **uv**: 依赖管理工具

### 启动 Mock 服务
```bash
cd mock_server/api_server
uv sync
uv run python base/flask_service.py
```

### 运行测试
```bash
uv sync
uv run python -m pytest -q --alluredir=./report/temp ./testcase --clean-alluredir --junitxml=./report/results.xml
```

### AI 结果分析
```bash
# Linux/macOS
export AI_API_KEY=your_deepseek_api_key
# Windows PowerShell
$env:AI_API_KEY="your_deepseek_api_key"

uv run python -m common.ai_agent
```

---

## 📄 License

[GPL-3.0](LICENSE)

基于 [youngyangyang04/Test-Automation-Framework](https://github.com/youngyangyang04/Test-Automation-Framework) 二次开发。
