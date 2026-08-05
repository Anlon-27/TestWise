# -*- coding: utf-8 -*-
"""
接口性能压测（Locust）

用法（先启动 mock server）：
    cd perf
    locust -f locustfile.py --host=http://127.0.0.1:8787
"""

from locust import HttpUser, between, task


class ApiPerfUser(HttpUser):
    """模拟真实用户：登录后高频调用商品列表等接口。"""

    wait_time = between(0.5, 2)

    def on_start(self):
        resp = self.client.post("/dar/user/login", data={"user_name": "test01", "passwd": "admin123"})
        try:
            self.token = resp.json().get("token")
        except Exception:
            self.token = None

    @task(3)
    def goods_list(self):
        self.client.get(
            "/coupApply/cms/goodsList",
            params={"msgType": "getHandsetListOfCust", "page": 1, "size": 20},
        )

    @task(1)
    def query_user(self):
        self.client.post("/dar/user/queryUser", data={"user_id": "123839387391912"})
