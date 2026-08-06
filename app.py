from __future__ import annotations

import html

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from signal_utils import (
    APP_NAME,
    ASSET_CATEGORY_MAP,
    ASSET_GROUPS,
    compute_snapshot,
    fetch_price_history,
    heatmap_style,
)


st.set_page_config(page_title=APP_NAME, layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def get_snapshot():
    raw_df = fetch_price_history()
    return compute_snapshot(raw_df)


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
            flat_columns.append(f"{col[0]}-{col[1]}")
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


def build_sortable_html_table(snapshot_table: pd.DataFrame) -> str:
    columns = list(snapshot_table.columns)
    group_map = {
        "资产名称": "",
        "资产分类": "",
        "趋势-1个月": "趋势",
        "趋势-3个月": "趋势",
        "趋势-6个月": "趋势",
        "反转-6个月": "反转",
        "反转-1年": "反转",
        "反转-2年": "反转",
        "波动-短期波动率": "波动",
        "波动-中期波动率": "波动",
    }

    group_spans = [("资产信息", 2), ("趋势", 3), ("反转", 3), ("波动", 2)]

    top_header = "".join(
        f'<th class="group-header" colspan="{span}">{label}</th>' for label, span in group_spans
    )

    second_header = []
    for idx, col in enumerate(columns):
        is_numeric = pd.api.types.is_numeric_dtype(snapshot_table[col])
        align_class = "text-left" if col in ("资产名称", "资产分类") else "text-center"
        sort_class = "sortable" if True else ""
        second_header.append(
            f'<th class="sub-header {align_class} {sort_class}" '
            f'data-col="{idx}" data-type="{"number" if is_numeric else "text"}">'
            f'{html.escape(col)}<span class="sort-indicator"></span></th>'
        )
    second_header_html = "".join(second_header)

    body_rows = []
    for _, row in snapshot_table.iterrows():
        cells = []
        for col in columns:
            value = row[col]
            group = group_map.get(col)
            style = heatmap_style(value, group=group)
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
st.caption("面向组合经理与研究员的多资产单资产信号看板")

toolbar_left, toolbar_right = st.columns([5, 1])
with toolbar_left:
    st.caption("默认按资产分类排序；点击任意具体信号列标题可重新排序。")
with toolbar_right:
    if st.button("刷新数据库", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    with st.spinner("正在连接数据库并计算最新信号..."):
        result = get_snapshot()
except Exception as exc:
    st.error(f"数据加载失败：{exc}")
    st.stop()

display_table = build_display_table(result.table)

summary_col1, summary_col2, summary_col3 = st.columns([1, 1, 3])
summary_col1.metric("资产数量", f"{len(display_table):,}")
summary_col2.metric("快照日期", result.snapshot_date.strftime("%Y-%m-%d"))
summary_col3.markdown(
    """
    <div class="info-card">
        <div class="info-card-title">信号组说明</div>
        <div class="info-card-body">
            <div><b>趋势</b>：<code>1</code> 最强做多，<code>-1</code> 最强做空</div>
            <div><b>反转</b>：<code>1</code> 跌幅最深、偏向抄底，<code>-1</code> 涨幅过大、偏向做空</div>
            <div><b>波动</b>：<code>0</code> 近期波动低位，<code>1</code> 近期波动高位</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

components.html(build_sortable_html_table(display_table), height=980, scrolling=True)
