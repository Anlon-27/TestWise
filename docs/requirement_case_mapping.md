# 需求-用例映射表

用于追溯"业务需求 → 测试模块 → 用例文件"，方便评估覆盖缺口与新人上手。

| 需求模块 | Allure feature | 用例文件 | 数据文件 |
| --- | --- | --- | --- |
| 用户管理（单接口） | 用户管理模块（单接口） | `testcase/Single interface/test_debug_api.py` | `addUser.yaml`、`updateUser.yaml`、`deleteUser.yaml`、`queryUser.yaml` |
| 商品管理（单接口） | 商品管理（单接口） | `testcase/ProductManager/test_productList.py` | `getProductList.yaml`、`productDetail.yaml`、`commitOrder.yaml`、`orderPay.yaml` |
| 业务链路（下单-支付-校验） | 业务场景 | `testcase/Business interface/test_business_scenario.py` | `BusinessScenario.yml` |

## 覆盖缺口提示

`pytest --cov=base --cov=common` 基线（当前用例集）约 32%，低覆盖模块：

- `common/handleExcel.py`、`common/operxml.py`、`common/semail.py`、`common/Pjenkins.py`（未被测试链路引用，属工具类，可补单元测试）
- `common/ai_agent.py`、`common/ai_tools.py`、`common/ai_report.py`（新功能模块，建议补单元测试）
- `base/apiutil_business.py` 与 `base/apiutil.py` 存在重复逻辑，可合并后提升覆盖

新用例建议：每个需求模块至少覆盖正向 / 反向 / 边界三类场景，并在 PR 描述中引用本表。
