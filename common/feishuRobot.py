# -*- coding: utf-8 -*-
"""
飞书自定义机器人推送
webhook 从 conf/config.ini [AI] feishu_webhook 读取，支持可选加签（feishu_secret）。
"""

import base64
import hashlib
import hmac
import time

import requests


def generate_sign(secret, timestamp):
    """飞书加签：timestamp + "\\n" + secret 做 HMAC-SHA256 后 base64。"""
    string_to_sign = "{}\n{}".format(timestamp, secret)
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def send_feishu_msg(content, webhook=None, secret=None):
    """
    推送文本消息到飞书机器人。
    :param content: 消息内容
    :param webhook: 机器人 webhook 完整地址；缺省读取 conf/config.ini [AI] feishu_webhook
    :param secret: 加签密钥（可选）
    :return: 接口返回文本
    """
    if not webhook:
        from conf.operationConfig import OperationConfig

        try:
            conf = OperationConfig().get_item_value("AI")
        except Exception:
            conf = {}
        webhook = (conf.get("feishu_webhook") or "").strip()
        secret = secret or (conf.get("feishu_secret") or "").strip() or None
    if not webhook:
        return "未配置飞书 webhook（conf/config.ini [AI] feishu_webhook）"

    payload = {"msg_type": "text", "content": {"text": str(content)[:4000]}}
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = generate_sign(secret, timestamp)
    resp = requests.post(webhook, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
    return resp.text
