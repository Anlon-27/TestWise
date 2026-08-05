import allure
import pytest

from base.apiutil import RequestBase
from common.readyaml import get_testcase_yaml
from common.recordlog import logs

"""
-function：每一个函数或方法都会调用
-class：每一个类调用一次，一个类中可以有多个方法
-module：每一个.py文件调用一次，该文件内又有多个function和class
-session：是多个文件调用一次，可以跨.py文件调用，每个.py文件就是module,整个会话只会运行一次
-autouse：默认为false，不会自动执行，需要手动调用，为true可以自动执行，不需要调用
- yield：前置、后置
"""


@pytest.fixture(autouse=True)
def start_test_and_end():
    logs.info('-------------接口测试开始--------------')
    yield
    logs.info('-------------接口测试结束--------------')


@pytest.fixture(scope='session', autouse=True)
@allure.story("登录")
def system_login():
    try:
        api_info = get_testcase_yaml('./data/loginName.yaml')
        RequestBase().specification_yaml(api_info[0][0], api_info[0][1])
    except Exception as e:
        logs.error(f'登录接口出现异常，导致后续接口无法继续运行，请检查程序！，{e}')
        exit()


@pytest.fixture(scope='session', autouse=True)
def datadb_init():
    """
    会话级数据治理占位。
    mock 数据备份/恢复已迁移到根 conftest.py 的 pytest_configure / pytest_sessionfinish
    （只在 master 进程执行，兼容 pytest-xdist 并行）。
    数据库场景可在此基础上扩展（预置数据 -> yield -> 清理）。
    """
    yield
