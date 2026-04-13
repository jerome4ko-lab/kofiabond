"""
국고채 30년 금리 데이터 수집 및 HTML 생성 스크립트
매일 GitHub Actions에서 실행됨
"""
import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import date, timedelta


def fetch_data():
    today = date.today().strftime('%Y%m%d')
    start = '20210101'

    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<message>
  <proframeHeader>
    <pfmAppName>BIS-KOFIABOND</pfmAppName>
    <pfmSvcName>BISLastAskPrcROPSrchSO</pfmSvcName>
    <pfmFnName>listTrm</pfmFnName>
  </proframeHeader>
  <systemHeader></systemHeader>
<BISComDspDatDTO><val1>DD</val1><val2>{start}</val2><val3>{today}</val3><val4>1530</val4><val5>3017</val5></BISComDspDatDTO></message>"""

    headers = {
        'Content-Type': 'application/xml; charset=utf-8',
        'Referer': 'https://kofiabond.or.kr/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    r = requests.post(
        'https://kofiabond.or.kr/proframeWeb/XMLSERVICES/',
        data=xml_body.encode('utf-8'),
        headers=headers,
        timeout=30
    )
    r.raise_for_status()
    return r.text


def parse_data(xml_text):
    root = ET.fromstring(xml_text)
    list_node = root.find('.//BISComDspDatListDTO')
    children = list_node.findall('BISComDspDatDTO')

    data = []
    for row in children:
        val1 = row.find('val1')
        val2 = row.find('val2')
        if val1 is None or val2 is None:
            continue
        date_str = val1.text
        rate_str = val2.text
        if not date_str or not rate_str:
            continue
        # 날짜 형식: YYYY-MM-DD (10자, 대시 포함)
        if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
            try:
                rate = float(rate_str)
                data.append([date_str, rate])
            except ValueError:
                continue
        # 날짜 형식: YYYYMMDD (8자리 숫자)
        elif len(date_str) == 8 and date_str.isdigit():
            formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            try:
                rate = float(rate_str)
                data.append([formatted, rate])
            except ValueError:
                continue

    # 날짜 오름차순 정렬
    data.sort(key=lambda x: x[0])
    return data


def generate_html(data):
    data_json = json.dumps(data)
    today_str = date.today().strftime('%Y-%m-%d')
    min_date = data[0][0] if data else '2021-01-01'
    max_date = data[-1][0] if data else today_str
    max_rate = max(r for _, r in data)
    min_rate = min(r for _, r in data)

    # Chart.js 및 annotation plugin 인라인
    chartjs_path = os.path.join(os.path.dirname(__file__), '_chartjs.js')
    annotation_path = os.path.join(os.path.dirname(__file__), '_annotation.js')

    with open(chartjs_path, 'r', encoding='utf-8') as f:
        chartjs = f.read()
    with open(annotation_path, 'r', encoding='utf-8') as f:
        annotation = f.read()

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>국고채 30년 금리 추이</title>
  <script>{chartjs}</script>
  <script>{annotation}</script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
      background: #0f1923;
      color: #e0e6f0;
      min-height: 100vh;
      padding: 32px 24px;
    }}
    .wrap {{ max-width: 1100px; margin: 0 auto; }}
    .header {{ margin-bottom: 28px; }}
    .header .sub {{ font-size: 13px; color: #6b7fa0; margin-bottom: 6px; }}
    .header h1 {{ font-size: 24px; font-weight: 700; color: #fff; }}
    .header .updated {{ font-size: 12px; color: #4a5a78; margin-top: 4px; }}
    .search-bar {{
      background: #162030; border: 1px solid #243448; border-radius: 12px;
      padding: 18px 24px; display: flex; align-items: center; gap: 16px;
      margin-bottom: 24px; flex-wrap: wrap;
    }}
    .search-bar label {{ font-size: 14px; color: #8a9bbf; white-space: nowrap; }}
    .search-bar input[type=date] {{
      background: #0f1923; border: 1px solid #2e4060; border-radius: 8px;
      color: #e0e6f0; padding: 8px 14px; font-size: 15px; font-family: inherit;
      outline: none; cursor: pointer; transition: border-color .2s;
    }}
    .search-bar input[type=date]:focus {{ border-color: #3b82f6; }}
    .search-bar input[type=date]::-webkit-calendar-picker-indicator {{ filter: invert(0.7); cursor: pointer; }}
    .btn {{
      background: #3b82f6; color: #fff; border: none; border-radius: 8px;
      padding: 9px 22px; font-size: 14px; font-family: inherit; font-weight: 600;
      cursor: pointer; transition: background .2s;
    }}
    .btn:hover {{ background: #2563eb; }}
    .stats {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 16px; margin-bottom: 24px;
    }}
    .stat-card {{
      background: #162030; border: 1px solid #243448; border-radius: 12px; padding: 20px 22px;
    }}
    .stat-card .label {{ font-size: 11px; color: #6b7fa0; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.8px; }}
    .stat-card .value {{ font-size: 26px; font-weight: 700; color: #fff; line-height: 1; }}
    .stat-card .sub {{ font-size: 12px; color: #6b7fa0; margin-top: 6px; }}
    .up {{ color: #f87171 !important; }}
    .down {{ color: #60a5fa !important; }}
    .neutral {{ color: #94a3b8 !important; }}
    .chart-card {{
      background: #162030; border: 1px solid #243448; border-radius: 16px;
      padding: 24px 24px 16px; margin-bottom: 24px;
    }}
    canvas {{ width: 100% !important; }}
    .table-card {{
      background: #162030; border: 1px solid #243448; border-radius: 12px; overflow: hidden;
    }}
    .table-card h2 {{
      font-size: 15px; font-weight: 600; color: #c8d6ef;
      padding: 18px 22px 14px; border-bottom: 1px solid #1e3050;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    thead th {{
      background: #1a2d44; color: #8a9bbf; padding: 10px 16px;
      text-align: center; font-weight: 600; font-size: 12px; letter-spacing: 0.3px;
    }}
    tbody td {{
      padding: 13px 16px; text-align: center;
      border-bottom: 1px solid #1a2a3e; color: #cdd8ee;
    }}
    tbody tr:last-child td {{ border-bottom: none; }}
    tbody tr:hover td {{ background: #1a2d44; }}
    .highlight-row td {{ background: #1b3352 !important; color: #fff !important; font-weight: 700; }}
    .dot-label {{
      display: inline-block; width: 9px; height: 9px;
      background: #f59e0b; border-radius: 50%; margin-right: 7px; vertical-align: middle;
    }}
    .no-result {{ text-align: center; color: #4a5a78; padding: 40px; font-size: 14px; }}
  </style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="sub">KOFIA BIS · 최종호가수익률 오후 기준 · {min_date} ~ {max_date}</div>
    <h1>국고채 30년 금리 추이</h1>
    <div class="updated">데이터 업데이트: {today_str} | 최고 {max_rate:.3f}% / 최저 {min_rate:.3f}%</div>
  </div>

  <div class="search-bar">
    <label>날짜 조회</label>
    <input type="date" id="queryDate" value="{max_date}" min="{min_date}" max="{max_date}">
    <button class="btn" onclick="queryByDate()">조회</button>
    <span id="queryMsg" style="font-size:13px;color:#6b7fa0;"></span>
  </div>

  <div class="stats">
    <div class="stat-card">
      <div class="label">조회 날짜</div>
      <div class="value" id="statDate">—</div>
      <div class="sub" id="statRate">금리 —</div>
    </div>
    <div class="stat-card">
      <div class="label">전일 대비</div>
      <div class="value" id="statDayDiff">—</div>
      <div class="sub" id="statDayPrev">—</div>
    </div>
    <div class="stat-card">
      <div class="label">전년 동일일 대비</div>
      <div class="value" id="statYearDiff">—</div>
      <div class="sub" id="statYearPrev">—</div>
    </div>
    <div class="stat-card">
      <div class="label">기간 내 백분위</div>
      <div class="value" id="statPct">—</div>
      <div class="sub">최고 {max_rate:.3f}% / 최저 {min_rate:.3f}%</div>
    </div>
  </div>

  <div class="chart-card">
    <canvas id="myChart" height="300"></canvas>
  </div>

  <div class="table-card">
    <h2 id="tableTitle">날짜를 조회하면 상세 결과가 표시됩니다</h2>
    <div id="tableContent">
      <div class="no-result">위에서 날짜를 선택하고 조회하세요</div>
    </div>
  </div>
</div>

<script>
const RAW = {data_json};
const dateMap = {{}};
RAW.forEach(([d, v]) => {{ dateMap[d] = v; }});
const labels = RAW.map(r => r[0]);
const values = RAW.map(r => r[1]);

let chart;

function makeGradient(ctx, area) {{
  const g = ctx.createLinearGradient(0, area.top, 0, area.bottom);
  g.addColorStop(0, 'rgba(59,130,246,0.4)');
  g.addColorStop(1, 'rgba(59,130,246,0.0)');
  return g;
}}

function buildChart() {{
  const ctx = document.getElementById('myChart').getContext('2d');
  chart = new Chart(ctx, {{
    type: 'line',
    data: {{
      labels,
      datasets: [
        {{
          label: '국고채 30년 (%)',
          data: values,
          borderColor: '#3b82f6',
          borderWidth: 1.8,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.3,
          fill: true,
          backgroundColor: (ctx2) => {{
            const area = ctx2.chart.chartArea;
            if (!area) return 'rgba(59,130,246,0.2)';
            return makeGradient(ctx2.chart.ctx, area);
          }},
        }},
        {{
          label: '조회 포인트',
          data: labels.map(() => null),
          pointRadius: labels.map(() => 0),
          pointBackgroundColor: '#f59e0b',
          pointBorderColor: '#fff',
          pointBorderWidth: 2.5,
          borderColor: 'transparent',
          backgroundColor: 'transparent',
        }}
      ]
    }},
    options: {{
      responsive: true,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          backgroundColor: '#1a2d44', borderColor: '#2e4060', borderWidth: 1,
          titleColor: '#8a9bbf', bodyColor: '#fff', padding: 12,
          callbacks: {{
            title: items => items[0].label,
            label: item => item.datasetIndex === 0 ? ' ' + item.raw.toFixed(3) + '%' : null,
          }}
        }},
        annotation: {{ annotations: {{}} }}
      }},
      scales: {{
        x: {{
          grid: {{ color: '#192a3e' }},
          ticks: {{
            color: '#4a5a78', font: {{ size: 11 }}, maxTicksLimit: 20,
            callback: function(val, i) {{
              const d = new Date(labels[i]);
              const mo = d.getMonth();
              const day = d.getDate();
              if (i === 0 || (mo % 3 === 0 && day <= 7)) return labels[i].slice(0, 7);
              return null;
            }}
          }}
        }},
        y: {{
          grid: {{ color: '#192a3e' }},
          ticks: {{ color: '#4a5a78', font: {{ size: 11 }}, callback: v => v.toFixed(2) + '%' }},
          min: 1.5, max: 5.0,
        }}
      }}
    }}
  }});
}}

function findClosest(target) {{
  if (dateMap[target] !== undefined) return target;
  const t = new Date(target);
  for (let d = 1; d <= 10; d++) {{
    for (const delta of [-d, d]) {{
      const nd = new Date(t);
      nd.setDate(nd.getDate() + delta);
      const ds = nd.toISOString().slice(0, 10);
      if (dateMap[ds] !== undefined) return ds;
    }}
  }}
  return null;
}}

function findPrevDay(target) {{
  const idx = labels.indexOf(target);
  return idx > 0 ? labels[idx - 1] : null;
}}

function findYearAgo(target) {{
  const t = new Date(target);
  t.setFullYear(t.getFullYear() - 1);
  return findClosest(t.toISOString().slice(0, 10));
}}

function signStr(v, dec) {{
  dec = dec || 3;
  const s = v.toFixed(dec);
  return v > 0 ? '+' + s : s;
}}
function cc(v) {{ return v > 0 ? 'up' : v < 0 ? 'down' : 'neutral'; }}

function queryByDate() {{
  const raw = document.getElementById('queryDate').value;
  if (!raw) return;
  const found = findClosest(raw);
  const msg = document.getElementById('queryMsg');
  if (!found) {{ msg.textContent = '데이터 없음'; return; }}
  msg.textContent = found !== raw ? '→ 가장 가까운 영업일: ' + found : '';

  const rate = dateMap[found];
  const idx = labels.indexOf(found);
  const prevDay = findPrevDay(found);
  const prevRate = prevDay ? dateMap[prevDay] : null;
  const dayDiff = prevRate != null ? rate - prevRate : null;
  const yearAgo = findYearAgo(found);
  const yearRate = yearAgo ? dateMap[yearAgo] : null;
  const yearDiff = yearRate != null ? rate - yearRate : null;
  const sorted = [...values].sort((a, b) => a - b);
  const pct = (sorted.filter(v => v <= rate).length / sorted.length * 100).toFixed(1);

  document.getElementById('statDate').textContent = found;
  document.getElementById('statRate').textContent = '금리 ' + rate.toFixed(3) + '%';

  function setCard(valId, subId, diff, prevD, prevR) {{
    const el = document.getElementById(valId);
    if (diff != null) {{
      el.textContent = signStr(diff) + '%p';
      el.className = 'value ' + cc(diff);
      document.getElementById(subId).textContent = (prevD || '') + ': ' + (prevR ? prevR.toFixed(3) + '%' : '—');
    }} else {{
      el.textContent = '—'; el.className = 'value neutral';
      document.getElementById(subId).textContent = '데이터 없음';
    }}
  }}
  setCard('statDayDiff', 'statDayPrev', dayDiff, prevDay, prevRate);
  setCard('statYearDiff', 'statYearPrev', yearDiff, yearAgo, yearRate);
  document.getElementById('statPct').textContent = pct + '%ile';

  const dotData = labels.map(() => null);
  dotData[idx] = rate;
  chart.data.datasets[1].data = dotData;
  chart.data.datasets[1].pointRadius = labels.map((_, i) => i === idx ? 10 : 0);
  chart.options.plugins.annotation.annotations = {{
    vline: {{
      type: 'line', xMin: idx, xMax: idx,
      borderColor: 'rgba(245,158,11,0.55)', borderWidth: 1.5, borderDash: [5, 4],
    }}
  }};
  chart.update('none');

  document.getElementById('tableTitle').textContent = found + ' 기준 상세 비교';
  const rows = [
    {{ lbl: '조회 날짜', date: found, r: rate, diff: null, hi: true }},
    {{ lbl: '전일', date: prevDay, r: prevRate, diff: dayDiff, hi: false }},
    {{ lbl: '전년 동일일', date: yearAgo, r: yearRate, diff: yearDiff, hi: false }},
  ];
  let tbl = '<table><thead><tr><th>구분</th><th>날짜</th><th>수익률</th><th>변동폭</th><th>방향</th></tr></thead><tbody>';
  rows.forEach(row => {{
    const cls = row.hi ? 'highlight-row' : '';
    const dot = row.hi ? '<span class="dot-label"></span>' : '';
    const rStr = row.r != null ? row.r.toFixed(3) + '%' : '—';
    let dStr = '—', arrow = '—', dCls = '';
    if (row.diff != null) {{
      dStr = signStr(row.diff) + '%p';
      arrow = row.diff > 0 ? '▲' : row.diff < 0 ? '▼' : '−';
      dCls = cc(row.diff);
    }}
    tbl += '<tr class="' + cls + '"><td>' + dot + row.lbl + '</td><td>' + (row.date || '—') + '</td><td>' + rStr + '</td><td class="' + dCls + '">' + dStr + '</td><td class="' + dCls + '">' + arrow + '</td></tr>';
  }});
  tbl += '</tbody></table>';
  document.getElementById('tableContent').innerHTML = tbl;
}}

buildChart();
queryByDate();
</script>
</body>
</html>"""
    return html


if __name__ == '__main__':
    print('데이터 수집 중...')
    xml_text = fetch_data()

    print('파싱 중...')
    data = parse_data(xml_text)
    print(f'  → {len(data)}행 수집 완료 ({data[0][0]} ~ {data[-1][0]})')

    print('HTML 생성 중...')
    html = generate_html(data)

    out_path = os.path.join(os.path.dirname(__file__), 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  → index.html 저장 완료 ({len(html):,} bytes)')
