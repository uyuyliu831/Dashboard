from __future__ import annotations

import html
import hmac
import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit.errors import StreamlitSecretNotFoundError

from signal_utils import (
    APP_NAME,
    ASSET_CATEGORY_MAP,
    ASSET_GROUPS,
    compute_snapshot,
    fetch_price_history,
    get_available_snapshot_dates,
    heatmap_style,
)


st.set_page_config(page_title=APP_NAME, layout="wide")


def get_app_password() -> str | None:
    try:
        secret_value = st.secrets.get("APP_PASSWORD")
        if secret_value:
            return str(secret_value)
    except StreamlitSecretNotFoundError:
        pass

    env_value = os.getenv("APP_PASSWORD")
    if env_value:
        return env_value

    return None


def check_password() -> bool:
    app_password = get_app_password()
    if not app_password:
        st.error("未配置访问密码，请设置 Streamlit secret 或环境变量 APP_PASSWORD。")
        return False

    def password_entered() -> None:
        entered_password = st.session_state.get("password", "")
        st.session_state["password_correct"] = hmac.compare_digest(entered_password, app_password)
        st.session_state["password"] = ""

    if st.session_state.get("password_correct", False):
        return True

    st.title(APP_NAME)
    st.subheader("访问验证")
    st.text_input("请输入访问密码", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("密码错误")
    return False


if not check_password():
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def get_price_history_data() -> pd.DataFrame:
    return fetch_price_history()


def ordered_categories() -> list[str]:
    return list(ASSET_GROUPS.keys())


def build_display_table(snapshot_table: pd.DataFrame) -> pd.DataFrame:
    table = snapshot_table.copy()
    table.insert(0, "资产分类", [ASSET_CATEGORY_MAP.get(name, "") for name in table.index])
    table.insert(0, "资产名称", table.index)
    table = table.reset_index(drop=True)
    table["资产分类"] = pd.Categorical(table["资产分类"], categories=ordered_categories(), ordered=True)
    table = table.sort_values(["资产分类", "资产名称"], kind="stable").reset_index(drop=True)

    flat_columns = []
    for col in table.columns:
        if isinstance(col, tuple):
            flat_columns.append(str(col[1]))
        else:
            flat_columns.append(str(col))
    table.columns = flat_columns
    return table


def format_value(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, str):
        return html.escape(value)
    return f"{float(value):.2f}"


def build_sortable_html_table(snapshot_table: pd.DataFrame, difference_mode: bool = False) -> str:
    columns = list(snapshot_table.columns)
    group_map = {
        "资产名称": "",
        "资产分类": "",
        "短期趋势-1个月": "资产趋势",
        "中期趋势-6个月": "资产趋势",
        "长期趋势-一年": "资产趋势",
        "短期偏度-6个月": "偏度反转",
        "中期偏度-一年": "偏度反转",
        "长期偏度-两年": "偏度反转",
        "短期波动-1个月": "波动",
        "中期波动-3个月": "波动",
        "长期波动-6个月": "波动",
    }

    group_spans = [("资产信息", 2), ("资产趋势", 3), ("偏度反转", 3), ("波动", 3)]
    top_header = "".join(
        f'<th class="group-header" colspan="{span}">{label}</th>' for label, span in group_spans
    )

    second_header = []
    for idx, col in enumerate(columns):
        is_numeric = pd.api.types.is_numeric_dtype(snapshot_table.iloc[:, idx])
        align_class = "text-left" if col in ("资产名称", "资产分类") else "text-center"
        second_header.append(
            f'<th class="sub-header {align_class} sortable" '
            f'data-col="{idx}" data-type="{"number" if is_numeric else "text"}">'
            f'{html.escape(col)}<span class="sort-indicator"></span></th>'
        )
    second_header_html = "".join(second_header)

    body_rows = []
    for _, row in snapshot_table.iterrows():
        cells = []
        for idx, col in enumerate(columns):
            value = row.iloc[idx]
            group = group_map.get(col)
            style = heatmap_style(value, group=group, difference_mode=difference_mode)
            align_class = "text-left" if col in ("资产名称", "资产分类") else "text-center"
            sort_value = "" if pd.isna(value) else (str(value) if isinstance(value, str) else f"{float(value):.10f}")
            cells.append(
                f'<td class="{align_class}" style="{style}" data-sort="{html.escape(sort_value)}">{format_value(value)}</td>'
            )
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    body_html = "".join(body_rows)

    return f"""
    <html>
    <head>
        <meta charset="utf-8" />
        <style>
            body {{
                margin: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                color: #334155;
                background: transparent;
            }}
            .table-wrap {{
                border: 1px solid #e7edf5;
                border-radius: 14px;
                overflow: auto;
                background: #ffffff;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
            }}
            table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                table-layout: fixed;
                font-size: 14px;
            }}
            col.name-col {{ width: 170px; }}
            col.category-col {{ width: 140px; }}
            col.signal-col {{ width: 110px; }}
            thead tr:first-child th {{
                position: sticky;
                top: 0;
                z-index: 3;
            }}
            thead tr:nth-child(2) th {{
                position: sticky;
                top: 42px;
                z-index: 4;
            }}
            .group-header {{
                background: #f7f9fc;
                color: #334155;
                font-weight: 650;
                text-align: center;
                padding: 12px 8px;
                border-bottom: 1px solid #e5ebf3;
                border-right: 1px solid #e7edf5;
            }}
            .group-header:last-child {{
                border-right: none;
            }}
            .sub-header {{
                background: #fbfcfe;
                color: #1f2a37;
                font-weight: 600;
                padding: 10px 8px;
                border-bottom: 1px solid #e5ebf3;
                border-right: 1px solid #edf2f7;
                cursor: pointer;
                user-select: none;
                white-space: nowrap;
            }}
            .sub-header:last-child {{
                border-right: none;
            }}
            .sub-header.sortable:hover {{
                background: #f3f6fb;
            }}
            td {{
                padding: 9px 10px;
                border-bottom: 1px solid #f1f5f9;
                border-right: 1px solid #f1f5f9;
                color: #243142;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            tbody td:last-child {{
                border-right: none;
            }}
            .text-left {{
                text-align: left;
            }}
            .text-center {{
                text-align: center;
            }}
            .sort-indicator {{
                display: inline-block;
                width: 14px;
                margin-left: 4px;
                color: #94a3b8;
                font-size: 11px;
            }}
            tbody tr:hover td {{
                box-shadow: inset 0 0 0 9999px rgba(248, 250, 252, 0.2);
            }}
        </style>
    </head>
    <body>
        <div class="table-wrap">
            <table id="signal-table">
                <colgroup>
                    <col class="name-col" />
                    <col class="category-col" />
                    <col class="signal-col" />
                    <col class="signal-col" />
                    <col class="signal-col" />
                    <col class="signal-col" />
                    <col class="signal-col" />
                    <col class="signal-col" />
                    <col class="signal-col" />
                    <col class="signal-col" />
                    <col class="signal-col" />
                </colgroup>
                <thead>
                    <tr>{top_header}</tr>
                    <tr>{second_header_html}</tr>
                </thead>
                <tbody>{body_html}</tbody>
            </table>
        </div>
        <script>
            const table = document.getElementById("signal-table");
            const tbody = table.querySelector("tbody");
            const headers = table.querySelectorAll(".sub-header");
            let sortState = {{ col: 1, dir: "asc" }};

            function applyIndicators() {{
                headers.forEach((header) => {{
                    const indicator = header.querySelector(".sort-indicator");
                    const col = Number(header.dataset.col);
                    if (col === sortState.col) {{
                        indicator.textContent = sortState.dir === "asc" ? "▲" : "▼";
                    }} else {{
                        indicator.textContent = "";
                    }}
                }});
            }}

            function sortRows(col, type, dir) {{
                const rows = Array.from(tbody.querySelectorAll("tr"));
                rows.sort((a, b) => {{
                    const aText = a.children[col].dataset.sort || "";
                    const bText = b.children[col].dataset.sort || "";

                    if (type === "number") {{
                        const aNum = aText === "" ? NaN : Number(aText);
                        const bNum = bText === "" ? NaN : Number(bText);
                        if (Number.isNaN(aNum) && Number.isNaN(bNum)) return 0;
                        if (Number.isNaN(aNum)) return 1;
                        if (Number.isNaN(bNum)) return -1;
                        return dir === "asc" ? aNum - bNum : bNum - aNum;
                    }}

                    return dir === "asc"
                        ? aText.localeCompare(bText, "zh-Hans-CN")
                        : bText.localeCompare(aText, "zh-Hans-CN");
                }});

                rows.forEach((row) => tbody.appendChild(row));
            }}

            headers.forEach((header) => {{
                header.addEventListener("click", () => {{
                    const col = Number(header.dataset.col);
                    const type = header.dataset.type;
                    const dir = sortState.col === col && sortState.dir === "asc" ? "desc" : "asc";
                    sortState = {{ col, dir }};
                    sortRows(col, type, dir);
                    applyIndicators();
                }});
            }});

            sortRows(sortState.col, headers[sortState.col].dataset.type, sortState.dir);
            applyIndicators();
        </script>
    </body>
    </html>
    """


def render_snapshot_block(result, title: str, description: str, difference_mode: bool = False) -> None:
    st.subheader(title)
    st.caption(description)

    display_table = build_display_table(result.table)

    summary_col1, summary_col2, summary_col3 = st.columns([1, 1, 3])
    summary_col1.metric("资产数量", f"{len(display_table):,}")
    summary_col2.metric("快照日期", result.snapshot_date.strftime("%Y-%m-%d"))
    summary_col3.markdown(
        """
        <div class="info-card">
            <div class="info-card-title">信号说明</div>
            <div class="info-card-body">
                <div><b>资产趋势</b>：<code>1</code> 偏多，<code>-1</code> 偏空</div>
                <div><b>偏度反转</b>：基于历史收益偏度，<code>1</code> 偏负偏度，<code>-1</code> 偏正偏度</div>
                <div><b>波动</b>：常规看板中 <code>0</code> 低波动、<code>1</code> 高波动；差值看板中为两日期之差</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    components.html(build_sortable_html_table(display_table, difference_mode=difference_mode), height=980, scrolling=True)


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1 {
        font-weight: 700 !important;
        letter-spacing: 0.2px;
        color: #1f2a37;
        margin-bottom: 0.2rem;
    }
    p, div, label {
        color: #334155;
    }
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e7edf5;
        border-radius: 14px;
        padding: 12px 14px;
    }
    div[data-testid="stMetric"] label {
        font-weight: 600;
    }
    .info-card {
        background: #f8fafc;
        border: 1px solid #e7edf5;
        border-radius: 14px;
        padding: 12px 14px;
        min-height: 104px;
        box-sizing: border-box;
    }
    .info-card-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #334155;
        margin-bottom: 0.35rem;
    }
    .info-card-body {
        font-size: 0.92rem;
        line-height: 1.55;
        color: #334155;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title(APP_NAME)
st.caption("默认显示最新可用结果；开启日历后可查询指定历史日期。若当天没有完整结果，会显示 No data。")

try:
    with st.spinner("正在连接数据库并加载历史数据…"):
        raw_df = get_price_history_data()
except Exception as exc:
    st.error(f"数据加载失败：{exc}")
    st.stop()

if raw_df.empty:
    st.info("No data")
    st.stop()

available_dates = get_available_snapshot_dates(raw_df)
if available_dates.empty:
    st.info("No data")
    st.stop()

min_calendar_date = available_dates.min().date()
max_calendar_date = available_dates.max().date()
latest_available_date = max_calendar_date
if len(available_dates) > 1:
    default_compare_older = available_dates[-2].date()
else:
    default_compare_older = latest_available_date

refresh_col, _ = st.columns([1, 5])
with refresh_col:
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

single_tab, range_tab = st.tabs(["单日期信号看板", "区间范围信号趋势"])

with single_tab:
    control_col1, control_col2 = st.columns([1.3, 1.4])
    with control_col1:
        use_historical_date = st.toggle("Use calendar date", value=False)
    with control_col2:
        selected_main_date = st.date_input(
            "Snapshot date",
            value=latest_available_date,
            min_value=min_calendar_date,
            max_value=max_calendar_date,
            disabled=not use_historical_date,
            key="main_snapshot_date",
        )

    if use_historical_date:
        with st.spinner("正在计算指定日期快照…"):
            main_result = compute_snapshot(raw_df, as_of_date=selected_main_date, exact_match=True)
    else:
        with st.spinner("正在计算最新快照…"):
            main_result = compute_snapshot(raw_df)

    if main_result is None:
        st.info("No data")
    else:
        description = (
            f"当前展示日期：{main_result.snapshot_date.strftime('%Y-%m-%d')}"
            if not use_historical_date
            else f"所选日期：{selected_main_date.strftime('%Y-%m-%d')}"
        )
        render_snapshot_block(main_result, "单日期信号看板", description)

with range_tab:
    st.caption("选择任意两个日期，返回 later minus older 的结果；如果任一日期没有完整结果，则显示 No data。")

    diff_col1, diff_col2 = st.columns(2)
    with diff_col1:
        diff_date_a = st.date_input(
            "Date A",
            value=default_compare_older,
            min_value=min_calendar_date,
            max_value=max_calendar_date,
            key="diff_date_a",
        )
    with diff_col2:
        diff_date_b = st.date_input(
            "Date B",
            value=latest_available_date,
            min_value=min_calendar_date,
            max_value=max_calendar_date,
            key="diff_date_b",
        )

    with st.spinner("正在计算双日期差值…"):
        diff_result_a = compute_snapshot(raw_df, as_of_date=diff_date_a, exact_match=True)
        diff_result_b = compute_snapshot(raw_df, as_of_date=diff_date_b, exact_match=True)

    if diff_result_a is None or diff_result_b is None:
        st.info("No data")
    else:
        older_result, later_result = sorted(
            [diff_result_a, diff_result_b],
            key=lambda item: item.snapshot_date,
        )
        diff_table = later_result.table.subtract(older_result.table)
        diff_table.index.name = older_result.table.index.name

        class DifferenceResult:
            def __init__(self, snapshot_date, table):
                self.snapshot_date = snapshot_date
                self.table = table

        diff_display_result = DifferenceResult(snapshot_date=later_result.snapshot_date, table=diff_table)
        render_snapshot_block(
            diff_display_result,
            "区间范围信号趋势",
            (
                f"Later: {later_result.snapshot_date.strftime('%Y-%m-%d')} | "
                f"Older: {older_result.snapshot_date.strftime('%Y-%m-%d')} | Formula: later - older"
            ),
            difference_mode=True,
        )
