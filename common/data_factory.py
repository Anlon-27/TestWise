# -*- coding: utf-8 -*-
"""
测试数据工厂
生成唯一、可识别的测试数据，避免用例之间数据冲突与脏数据残留。
"""

import random
import time


def unique_suffix():
    """毫秒时间戳 + 随机数，保证同一秒内多次调用也不重复。"""
    return "{}{:04d}".format(int(time.time() * 1000) % 100000000, random.randint(0, 9999))


def username(prefix="test"):
    """生成唯一用户名，如 test_1234567890_1234。"""
    return "{}_{}".format(prefix, unique_suffix())


def phone():
    """生成 11 位手机号。"""
    return "13{}".format(random.randint(100000000, 999999999))


def role_id():
    """生成随机角色 ID。"""
    return random.randint(100000000, 999999999)


def order_number():
    """生成 18 位订单号。"""
    return str(random.randint(10**17, 10**18 - 1))


def user_id():
    """生成 19 位用户 ID。"""
    return str(random.randint(10**18, 10**19 - 1))


def timestamp_10():
    """10 位时间戳。"""
    return int(time.time())


def timestamp_13():
    """13 位时间戳。"""
    return int(time.time() * 1000)
