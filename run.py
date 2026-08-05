import os
import shutil
import sys
import webbrowser

import pytest

from conf.operationConfig import OperationConfig
from conf.setting import REPORT_TYPE


def parallel_args():
    """读取 [PARALLEL] 配置，返回 pytest 并行执行参数（未启用时返回空列表）。"""
    try:
        conf = OperationConfig().get_item_value("PARALLEL")
    except Exception:
        return []
    if str(conf.get("enable", "false")).strip().lower() not in ("true", "1", "yes"):
        return []
    workers = str(conf.get("workers", "0") or "0").strip()
    return ["-n", "auto" if workers in ("0", "") else workers]


def run_ai_analysis():
    """测试结束后运行 AI 结果解读（[AI] enable=false 时静默跳过）。"""
    try:
        from common.ai_agent import analyze_test_result

        analyze_test_result()
    except Exception as e:
        print("AI 结果解读失败: {}".format(e))


def ensure_output_dirs():
    """统一生成目录：所有日志/报告/运行时产物都落在 report/ 下。"""
    for sub in ("report/logs", "report/coverage", "report/mock_server"):
        os.makedirs(os.path.join(os.getcwd(), sub), exist_ok=True)
    os.environ["COVERAGE_FILE"] = os.path.join(os.getcwd(), "report", "coverage", ".coverage")


if __name__ == "__main__":
    ensure_output_dirs()

    if "--analyze" in sys.argv:
        # 仅分析已有报告，不重新执行测试
        run_ai_analysis()
        sys.exit(0)

    if REPORT_TYPE == "allure":
        pytest.main(
            ["-s", "-v", "--alluredir=./report/temp", "./testcase", "--clean-alluredir"]
            + parallel_args()
            + [
                "--reruns",
                "2",
                "--reruns-delay",
                "1",
                "--only-rerun",
                "ConnectionError|TimeoutError|连接异常|请求超时",
                "--cov=base",
                "--cov=common",
                "--cov-report=term",
                "--cov-report=html:report/coverage",
                "--junitxml=./report/results.xml",
            ]
        )

        shutil.copy("./environment.xml", "./report/temp")
        run_ai_analysis()
        os.system("allure serve ./report/temp")

    elif REPORT_TYPE == "tm":
        pytest.main(
            ["-vs", "--pytest-tmreport-name=testReport.html", "--pytest-tmreport-path=./report/tmreport"]
            + parallel_args()
            + ["--reruns", "2", "--reruns-delay", "1", "--only-rerun", "ConnectionError|TimeoutError|连接异常|请求超时"]
        )
        webbrowser.open_new_tab(os.getcwd() + "/report/tmreport/testReport.html")
        run_ai_analysis()
