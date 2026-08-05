# -*- coding: utf-8 -*-
"""响应时间统计：从 report/results.xml 计算用例耗时分布（P50/P90/P95/P99）。"""

import os
import statistics
import xml.etree.ElementTree as ET

from conf import setting


def compute_perf_stats(xml_path=None):
    """读取 JUnit 报告并返回各用例耗时分布统计。"""
    xml_path = xml_path or os.path.join(setting.DIR_BASE, "report", "results.xml")
    if not os.path.exists(xml_path):
        return {"error": "未找到 {}".format(xml_path)}
    try:
        root = ET.parse(xml_path).getroot()
    except Exception as e:
        return {"error": "解析 results.xml 失败: {}".format(e)}

    times = []
    suites = root.findall("testsuite") or ([root] if root.tag == "testsuite" else [])
    for suite in suites:
        for tc in suite.iter("testcase"):
            try:
                times.append(float(tc.get("time")))
            except (TypeError, ValueError):
                continue
    if not times:
        return {"total_cases": 0, "message": "没有可用耗时数据"}

    times.sort()

    def percentile(p):
        k = (len(times) - 1) * p
        f = int(k)
        c = min(f + 1, len(times) - 1)
        return times[f] + (times[c] - times[f]) * (k - f)

    return {
        "total_cases": len(times),
        "total_time_s": round(sum(times), 3),
        "mean_s": round(statistics.mean(times), 3),
        "min_s": round(times[0], 3),
        "max_s": round(times[-1], 3),
        "p50_s": round(percentile(0.50), 3),
        "p90_s": round(percentile(0.90), 3),
        "p95_s": round(percentile(0.95), 3),
        "p99_s": round(percentile(0.99), 3),
        "source": xml_path,
    }
