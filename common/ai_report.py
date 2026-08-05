# -*- coding: utf-8 -*-
"""
AI 测试结果分析报告渲染
把 agent 的最终分析（Markdown 文本）渲染成美化的 HTML 页面，保存到 report/ai_report.html。
"""

import html
import os
import re
import time
import xml.etree.ElementTree as ET

from conf import setting


def _inline(text):
    """处理行内格式：**加粗**、`代码`、*斜体*（先转义 HTML）。"""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def _table(lines):
    """把连续的 Markdown 表格行渲染成 HTML 表格。"""
    header = None
    body_rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
            continue  # 分隔行
        if header is None:
            header = cells
        else:
            body_rows.append(cells)
    thead = "".join("<th>{}</th>".format(_inline(c)) for c in (header or []))
    tbody = "".join("<tr>{}</tr>".format("".join("<td>{}</td>".format(_inline(c)) for c in row)) for row in body_rows)
    return '<div class="table-wrap"><table><thead><tr>{}</tr></thead><tbody>{}</tbody></table></div>'.format(
        thead, tbody
    )


def markdown_to_html(text):
    """轻量 Markdown 渲染，覆盖报告常用的标题/表格/列表/代码块/引用/段落。"""
    text = (text or "").replace("\r\n", "\n")
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            out.append("<pre><code>{}</code></pre>".format(html.escape("\n".join(code))))
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            out.append("<h{0}>{1}</h{0}>".format(level, _inline(m.group(2))))
            i += 1
            continue

        if stripped.startswith("|"):
            table = [lines[i]]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table.append(lines[i])
                i += 1
            out.append(_table(table))
            continue

        if stripped in ("---", "***", "___"):
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith(("- ", "* ")):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append("<li>{}</li>".format(_inline(lines[i].strip()[2:].strip())))
                i += 1
            out.append("<ul>{}</ul>".format("".join(items)))
            continue

        if re.match(r"^\s*\d+\.\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append("<li>{}</li>".format(_inline(re.sub(r"^\s*\d+\.\s+", "", lines[i]).strip())))
                i += 1
            out.append("<ol>{}</ol>".format("".join(items)))
            continue

        if stripped.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote>{}</blockquote>".format(_inline(" ".join(quote))))
            continue

        if not stripped:
            out.append("")
            i += 1
            continue

        out.append("<p>{}</p>".format(_inline(stripped)))
        i += 1

    return "\n".join(out)


def _load_stats():
    """从 report/results.xml 读取统计信息，用于页面顶部指标卡。"""
    xml_path = os.path.join(setting.DIR_BASE, "report", "results.xml")
    if not os.path.exists(xml_path):
        return {}
    try:
        suite = ET.parse(xml_path).getroot().find("testsuite")
    except Exception:
        return {}
    if suite is None:
        return {}
    stats = {}
    for key in ("tests", "failures", "errors", "skipped", "time", "timestamp", "hostname"):
        if suite.get(key) is not None:
            stats[key] = suite.get(key)
    try:
        stats["passed"] = str(
            int(stats.get("tests", 0))
            - int(stats.get("failures", 0))
            - int(stats.get("errors", 0))
            - int(stats.get("skipped", 0))
        )
    except (TypeError, ValueError):
        stats["passed"] = "—"
    return stats


def render_analysis_html(final_text, out_path=None, extra=None):
    """把 agent 的最终分析渲染为 HTML 文件，返回文件绝对路径。"""
    extra = extra or {}
    stats = _load_stats()
    body = markdown_to_html(final_text) or "<p>（agent 未返回分析内容）</p>"
    tools = "、".join(extra.get("tools_used") or ["—"]) or "—"

    cards = [
        ("用例总数", stats.get("tests", "—"), "total"),
        ("通过", stats.get("passed", "—"), "pass"),
        ("失败", stats.get("failures", "—"), "fail"),
        ("错误", stats.get("errors", "—"), "error"),
        ("跳过", stats.get("skipped", "—"), "skip"),
    ]
    cards_html = "".join(
        '<div class="stat {0}"><div class="num">{1}</div><div class="label">{2}</div></div>'.format(cls, val, label)
        for label, val, cls in cards
    )

    html_doc = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TestWise 智能接口测试框架 | 测试结果分析报告</title>
<style>
:root {{
  --pass: #16a34a; --fail: #dc2626; --error: #d97706; --skip: #64748b;
  --ink: #1e293b; --muted: #64748b; --bg: #f1f5f9; --card: #ffffff;
  --line: #e2e8f0; --accent: #4f46e5; --accent2: #7c3aed;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink);
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  line-height: 1.75; }}
.hero {{ background: linear-gradient(135deg, var(--accent), var(--accent2)); color: #fff;
  padding: 40px 24px 56px; }}
.hero .inner {{ max-width: 960px; margin: 0 auto; }}
.hero h1 {{ margin: 0 0 8px; font-size: 26px; letter-spacing: .5px; }}
.hero .meta {{ opacity: .92; font-size: 13px; }}
.wrap {{ max-width: 960px; margin: -34px auto 48px; padding: 0 16px; }}
.stats {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }}
.stat {{ background: var(--card); border-radius: 14px; padding: 18px 10px; text-align: center;
  box-shadow: 0 8px 24px rgba(15, 23, 42, .08); border: 1px solid var(--line); }}
.stat .num {{ font-size: 30px; font-weight: 700; }}
.stat .label {{ font-size: 13px; color: var(--muted); margin-top: 2px; }}
.stat.total .num {{ color: var(--accent); }}
.stat.pass .num {{ color: var(--pass); }}
.stat.fail .num {{ color: var(--fail); }}
.stat.error .num {{ color: var(--error); }}
.stat.skip .num {{ color: var(--skip); }}
.card {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: 28px 32px; box-shadow: 0 8px 24px rgba(15, 23, 42, .06); }}
.card h1 {{ font-size: 24px; margin: 28px 0 10px; padding-bottom: 8px;
  border-bottom: 2px solid var(--line); }}
.card h1:first-child {{ margin-top: 0; }}
.card h2 {{ font-size: 20px; margin: 26px 0 8px; color: var(--accent); }}
.card h3 {{ font-size: 16px; margin: 20px 0 6px; }}
.card p {{ margin: 8px 0; }}
.card ul, .card ol {{ margin: 8px 0 8px 4px; padding-left: 22px; }}
.card li {{ margin: 4px 0; }}
.card code {{ background: #eef2ff; color: #4338ca; border-radius: 5px;
  padding: 2px 6px; font-size: 13px; }}
.card pre {{ background: #0f172a; color: #e2e8f0; border-radius: 10px; padding: 14px 16px;
  overflow-x: auto; }}
.card pre code {{ background: none; color: inherit; padding: 0; }}
.card blockquote {{ margin: 12px 0; padding: 10px 16px; border-left: 4px solid var(--accent);
  background: #eef2ff; border-radius: 0 8px 8px 0; }}
.table-wrap {{ overflow-x: auto; margin: 12px 0; border: 1px solid var(--line); border-radius: 10px; }}
.card table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
.card th {{ background: #f8fafc; color: var(--muted); text-align: left; padding: 10px 14px;
  border-bottom: 1px solid var(--line); white-space: nowrap; }}
.card td {{ padding: 10px 14px; border-bottom: 1px solid var(--line); }}
.card tr:last-child td {{ border-bottom: none; }}
.card tbody tr:nth-child(even) {{ background: #f8fafc; }}
.foot {{ margin-top: 20px; color: var(--muted); font-size: 12.5px; line-height: 2; }}
.foot span {{ background: #e2e8f0; color: #475569; border-radius: 999px; padding: 3px 10px; margin-right: 6px; }}
@media (max-width: 640px) {{
  .stats {{ grid-template-columns: repeat(2, 1fr); }}
  .card {{ padding: 20px 16px; }}
}}
</style>
</head>
<body>
<header class="hero">
  <div class="inner">
    <h1>TestWise 智能接口测试框架</h1>
    <div class="meta">AI 测试结果分析报告 · 生成时间：{generated} · 模型：{model}</div>
  </div>
</header>
<div class="wrap">
  <section class="stats">{cards}</section>
  <article class="card">{body}</article>
  <div class="foot">
    <div><span>数据来源</span>{sources}</div>
    <div><span>Agent 调用工具</span>{tools}</div>
    <div>报告文件：report/ai_report.html</div>
  </div>
</div>
</body>
</html>""".format(
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        model=extra.get("model") or "—",
        cards=cards_html,
        body=body,
        tools=tools,
        sources="report/results.xml、report/temp/（Allure 原始结果）、report/logs/（运行日志）",
    )

    out_path = out_path or os.path.join(setting.DIR_BASE, "report", "ai_report.html")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return out_path
