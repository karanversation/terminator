"""
Utility functions for Transaction Analyzer
"""

import html as _html

import pandas as pd
import streamlit.components.v1 as _components


def format_inr(amount):
    """
    Format amount in Indian numbering system (lakhs, crores)
    
    Args:
        amount: Numerical amount to format
        
    Returns:
        Formatted string in Indian numbering with rupee symbol (₹1,23,456.00)
    """
    if pd.isna(amount):
        return "₹0"
    
    # Handle negative numbers
    is_negative = amount < 0
    amount = abs(amount)
    
    # Convert to string and split into integer and decimal parts
    amount_str = f"{amount:.2f}"
    parts = amount_str.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else "00"
    
    # Indian numbering system: groups of 3 from right, then groups of 2
    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        # Last 3 digits
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        
        # Group remaining digits in pairs from right to left
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        
        # Reverse and join
        groups.reverse()
        formatted = ','.join(groups) + ',' + last_three
    
    result = f"₹{formatted}.{decimal_part}"
    return f"-{result}" if is_negative else result


def render_txn_table(df: pd.DataFrame, columns: list, height: int = 500) -> None:
    """
    Render a transaction table as scrollable HTML with hover tooltips on Description.
    df should include 'raw_description' and 'Type' alongside any display columns.
    Amount may be numeric or already-formatted string; both are handled.
    """
    header_html = ''.join(f'<th>{_html.escape(c)}</th>' for c in columns)
    rows = []

    for i in range(len(df)):
        row = df.iloc[i]
        txn_type = str(row['Type']) if 'Type' in df.columns and pd.notna(row.get('Type')) else ''

        # Prefer literal file row; fall back to reconstructing from parsed fields
        raw_line_val = str(row.get('raw_line', '')).strip() if 'raw_line' in df.columns else ''
        if raw_line_val and raw_line_val not in ('nan', 'None'):
            full_tip = _html.escape(raw_line_val)
        else:
            # Reconstruct from available fields
            d = row['Date'] if 'Date' in df.columns else None
            date_part = d.strftime('%d/%m/%Y') if d is not None and hasattr(d, 'strftime') else ''
            raw_narr = str(row.get('raw_description', '') or '').strip()
            amt_val = row['Amount'] if 'Amount' in df.columns else None
            amt_part = format_inr(amt_val) if amt_val is not None and not isinstance(amt_val, str) and pd.notna(amt_val) else str(amt_val or '')
            parts = [p for p in [date_part, raw_narr, amt_part, txn_type] if p and p not in ('nan', 'None')]
            full_tip = _html.escape(' | '.join(parts) if parts else '—')

        cells = ''
        for col in columns:
            val = row[col] if col in df.columns else ''
            if col == 'Date':
                cell_str = val.strftime('%d %b %Y') if hasattr(val, 'strftime') else _html.escape(str(val))
                cells += f'<td>{cell_str}</td>'
            elif col == 'Amount':
                if isinstance(val, str):
                    amt_disp = _html.escape(val)
                elif pd.notna(val):
                    amt_disp = _html.escape(format_inr(val))
                else:
                    amt_disp = '—'
                if txn_type == 'Debit':
                    style = 'color:#e74c3c;font-weight:bold'
                elif txn_type == 'Credit':
                    style = 'color:#27ae60;font-weight:bold'
                else:
                    style = ''
                cells += f'<td style="{style}">{amt_disp}</td>'
            elif col == 'Description':
                cells += f'<td class="desc" data-raw="{full_tip}">{_html.escape(str(val or ""))}</td>'
            else:
                cells += f'<td>{_html.escape(str(val) if pd.notna(val) else "")}</td>'
        rows.append(f'<tr>{cells}</tr>')

    table_html = f"""<!DOCTYPE html><html><head><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:transparent; font-family:"Source Sans Pro",sans-serif; font-size:13px; color:#fafafa; }}
table {{ border-collapse:collapse; width:100%; }}
th {{ padding:8px 10px; text-align:left; color:#aaa; font-weight:600;
      border-bottom:2px solid #333; white-space:nowrap; background:#0e1117; }}
td {{ padding:6px 10px; border-bottom:1px solid #1e2130; vertical-align:middle; }}
tr:hover td {{ background:rgba(255,255,255,0.05); }}
td.desc {{ max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
#tip {{
    position:fixed; display:none; background:#2a2a2a; color:#fff;
    padding:6px 12px; border-radius:5px; font-size:12px;
    white-space:pre; z-index:9999; pointer-events:none;
    border:1px solid #555; box-shadow:0 2px 8px rgba(0,0,0,0.5); line-height:1.6;
}}
</style></head><body>
<div id="tip"></div>
<table><thead><tr>{header_html}</tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<script>
var tip = document.getElementById('tip');
document.addEventListener('mousemove', function(e) {{
    var td = e.target.closest('td.desc');
    if (td) {{
        var raw = td.getAttribute('data-raw');
        if (raw) {{
            tip.textContent = raw;
            tip.style.display = 'block';
            tip.style.left = (e.clientX + 14) + 'px';
            tip.style.top  = (e.clientY + 14) + 'px';
        }}
    }} else {{
        tip.style.display = 'none';
    }}
}});
</script>
</body></html>"""

    _components.html(table_html, height=height, scrolling=True)

