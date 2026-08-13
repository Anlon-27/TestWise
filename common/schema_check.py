# -*- coding: utf-8 -*-
"""
轻量 JSON Schema 校验（契约测试）
用于在 YAML validation 中声明响应结构：{"required": {...}, "optional": {...}}。
"""

TYPE_MAP = {
    "str": str,
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "bool": bool,
    "boolean": bool,
    "dict": dict,
    "object": dict,
    "list": list,
    "array": list,
    "none": type(None),
    "nonetype": type(None),
}


def _normalize_type(expected_type):
    """兼容 YAML 写法（'str'/'int'...）与 Python 类型写法（str/int...）。"""
    if isinstance(expected_type, str):
        return TYPE_MAP.get(expected_type.lower(), expected_type)
    return expected_type


def validate_schema(actual, schema):
    """校验实际响应是否符合 schema，返回 (ok, errors)。"""
    errors = []
    if not isinstance(actual, dict):
        return False, ["实际响应不是对象"]
    required = schema.get("required") or {}
    optional = schema.get("optional") or {}
    for field, expected_type in required.items():
        expected_type = _normalize_type(expected_type)
        if isinstance(expected_type, str):
            errors.append("schema 类型声明错误: {} = {}".format(field, expected_type))
            continue
        if field not in actual:
            errors.append("缺少必填字段: {}".format(field))
        elif actual[field] is not None and not isinstance(actual[field], expected_type):
            errors.append("字段 {} 类型应为 {}，实际为 {}".format(
                field, expected_type.__name__, type(actual[field]).__name__))
    for field, expected_type in optional.items():
        expected_type = _normalize_type(expected_type)
        if isinstance(expected_type, str):
            errors.append("schema 类型声明错误: {} = {}".format(field, expected_type))
            continue
        if field in actual and actual[field] is not None and not isinstance(actual[field], expected_type):
            errors.append("字段 {} 类型应为 {}，实际为 {}".format(
                field, expected_type.__name__, type(actual[field]).__name__))
    return not errors, errors
