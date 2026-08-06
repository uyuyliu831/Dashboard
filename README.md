# 多资产信号罗盘

一个基于 Streamlit 的中文仪表盘，用于跟踪单资产的趋势、反转和波动信号，面向组合经理与研究员。

## 当前版本特点

- 资产名称 + 资产分类双列展示
- 默认按资产分类、资产名称排序
- 每个具体信号列都支持点击排序
- 两层表头：资产信息 / 趋势 / 反转 / 波动
- 数值统一保留 2 位小数
- 使用柔和的红 - 白 - 蓝热力配色
- 直接连接 MySQL 数据库

## 指标口径

- **趋势（MOMCO）**
  - 短窗固定为 5 天
  - 长窗分别为 1 个月、3 个月、6 个月
  - 最终缩放到 `[-1, 1]`
  - `1` 代表最强做多，`-1` 代表最强做空

- **反转（SKNS）**
  - 基于日对数收益率
  - 展示 6 个月、1 年、2 年版本
  - 最终缩放到 `[-1, 1]`
  - `1` 代表近期跌幅最深、偏向抄底，`-1` 代表近期涨幅过大、偏向做空

- **波动**
  - 短期波动率：1 年内 1 个月波动的滚动 Z 分数
  - 中期波动率：2 年内 3 个月波动的滚动 Z 分数
  - 最终缩放到 `[0, 1]`
  - `0` 代表近期波动低位，`1` 代表近期波动高位

## 本地运行

```bash
cd C:\Projects\Dashboard
C:\Users\qinxi\anaconda3\python.exe -m pip install -r requirements.txt
C:\Users\qinxi\anaconda3\python.exe -m streamlit run app.py
```

## 说明

- 当前版本已在代码中写死数据库连接配置
- 如需覆盖，也可使用环境变量：
  `DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME / DB_TABLE`

## 主要文件

```text
app.py
signal_utils.py
requirements.txt
README.md
```
