# -*- coding: utf-8 -*-
import os
import shutil
import time
import warnings

import pytest

from base.removefile import remove_file
from common.dingRobot import send_dd_msg
from common.readyaml import ReadYamlData
from conf.setting import DIR_BASE, dd_msg

yfd = ReadYamlData()

MOCK_DATA_DIR = os.path.join(DIR_BASE, 'mock_server', 'api_server', 'data', 'mockdata')
MOCK_DATA_FILES = ['userManage.json', 'orderNumber.json']
MOCK_DATA_BACKUP_DIR = os.path.join(DIR_BASE, 'report', 'data_backup')


def backup_mock_data():
    """会话开始前备份 mock 持久化数据。"""
    os.makedirs(MOCK_DATA_BACKUP_DIR, exist_ok=True)
    for name in MOCK_DATA_FILES:
        src = os.path.join(MOCK_DATA_DIR, name)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(MOCK_DATA_BACKUP_DIR, name))


def restore_mock_data():
    """会话结束后恢复 mock 持久化数据，保证测试不产生脏数据。"""
    for name in MOCK_DATA_FILES:
        dst = os.path.join(MOCK_DATA_DIR, name)
        src = os.path.join(MOCK_DATA_BACKUP_DIR, name)
        if os.path.exists(src):
            shutil.copyfile(src, dst)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # pytest-xdist 下只在 master 进程备份，避免各 worker 竞争写入
    if not hasattr(config, 'workerinput'):
        backup_mock_data()


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    # 只在 master 进程恢复，避免 worker 各自恢复导致数据不一致
    if not hasattr(session.config, 'workerinput'):
        restore_mock_data()


@pytest.fixture(scope="session", autouse=True)
def clear_extract():
    # 禁用HTTPS告警，ResourceWarning
    warnings.simplefilter('ignore', ResourceWarning)

    # pytest-xdist 并行时，每个 worker 使用独立的 extract 文件，避免变量互相覆盖
    worker = os.environ.get('PYTEST_XDIST_WORKER')
    if worker:
        os.environ['EXTRACT_FILE'] = os.path.join(DIR_BASE, 'report', 'extract_{}.yaml'.format(worker))
    yfd.clear_yaml_data()
    if not worker or worker == 'gw0':
        remove_file("./report/temp", ['json', 'txt', 'attach', 'properties'])

    yield

    if worker:
        os.environ.pop('EXTRACT_FILE', None)
        worker_file = os.path.join(DIR_BASE, 'report', 'extract_{}.yaml'.format(worker))
        if os.path.exists(worker_file):
            os.remove(worker_file)


def generate_test_summary(terminalreporter):
    """生成测试结果摘要字符串"""
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    error = len(terminalreporter.stats.get('error', []))
    skipped = len(terminalreporter.stats.get('skipped', []))
    # xdist 并行下 _numcollected 可能为 0，用统计值求和保证准确
    total = passed + failed + error + skipped
    # pytest 8 使用 _sessionstarttime（float），pytest 9 改名为 _session_start（Instant，提供 elapsed()），这里做兼容
    session_start = getattr(terminalreporter, '_sessionstarttime', None)
    if session_start is None:
        session_start = getattr(terminalreporter, '_session_start', None)
    duration = 0.0
    if hasattr(session_start, 'elapsed'):
        elapsed = session_start.elapsed()
        duration = getattr(elapsed, 'seconds', None) or 0.0
    elif isinstance(session_start, (int, float)):
        duration = time.time() - session_start

    summary = f"""
    自动化测试结果，通知如下，请着重关注测试失败的接口，具体执行结果如下：
    测试用例总数：{total}
    测试通过数：{passed}
    测试失败数：{failed}
    错误数量：{error}
    跳过执行数量：{skipped}
    执行总时长：{duration}
    """
    print(summary)
    return summary


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """自动收集pytest框架执行的测试结果并打印摘要信息"""
    summary = generate_test_summary(terminalreporter)
    if dd_msg:
        send_dd_msg(summary)
