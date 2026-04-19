import streamlit as st
from datetime import date, timedelta
from itertools import permutations
import jra_scraper
import external_scores as ext

st.set_page_config(
    page_title="uma姫AI 予想ビルダー",
    page_icon="🌸",
    layout="wide",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #0f0a14; color: #f0e6f0; }
[data-testid="stHeader"] { background-color: #0f0a14; }
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #6b1a3a, #9b2d5a);
    color: #fff;
    border: 1px solid #c8527a;
    border-radius: 8px;
    font-weight: bold;
}
[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #8b2a5a, #c8527a);
}
[data-testid="stSelectbox"] label { color: #f0c0d0; }
hr { border-color: #2a1a2a; }

.umahime-logo {
    font-size: 2rem; font-weight: 900; letter-spacing: -1px; color: #fff;
}
.umahime-logo span { color: #ff8fab; }
.umahime-sub { font-size: 0.8rem; color: #c87a9a; letter-spacing: 2px; }

.mark-hon  { color: #ff4444; font-weight: 900; font-size: 1.3rem; }
.mark-tai  { color: #ff8c00; font-weight: 900; font-size: 1.3rem; }
.mark-tan  { color: #22cc88; font-weight: 900; font-size: 1.3rem; }
.mark-ren  { color: #55aaff; font-weight: 900; font-size: 1.2rem; }
.mark-ana  { color: #cc66ff; font-weight: 900; font-size: 1.2rem; }
.mark-none { color: #444; font-size: 1.2rem; }

.score-pos { color: #ff6680; font-weight: bold; }
.score-neu { color: #88aacc; font-weight: bold; }
.score-neg { color: #666; font-weight: bold; }

.trifecta-box {
    background: #1a0f1f;
    border: 1px solid #4a1a3a;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 8px 0;
}
.trifecta-title { color: #ff8fab; font-weight: bold; font-size: 0.9rem; margin-bottom: 8px; }
.trifecta-combo { color: #f0e6f0; font-size: 0.95rem; line-height: 2; }

.eval-box {
    background: #150d20;
    border-left: 3px solid #ff8fab;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    margin: 12px 0;
    color: #e0c8d8;
    font-size: 0.9rem;
    line-height: 1.8;
}
.mikoto-name { color: #ff8fab; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ━━━━━━━ ヘッダー ━━━━━━━
st.markdown("""
<div style="margin-bottom:8px;">
  <div class="umahime-logo">uma<span>姫</span>AI</div>
  <div class="umahime-sub">🌸 MIKOTO PREDICTION SYSTEM 🌸</div>
</div>
""", unsafe_allow_html=True)
st.divider()

# ━━━━━━━ 日付・取得 ━━━━━━━
col_date, col_btn = st.columns([2, 1])
with col_date:
    today = date.today()
    target_date = st.date_input(
        "日付",
        value=today + timedelta(days=1),
        min_value=today,
        max_value=today + timedelta(days=7),
        label_visibility="collapsed",
    )
with col_btn:
    fetch_btn = st.button("🔍 レース一覧を取得", use_container_width=True)

if fetch_btn:
    with st.spinner("レース一覧を取得中..."):
        st.session_state.race_list = jra_scraper.get_race_list(target_date)
        st.session_state.loaded_date = target_date
        st.session_state.pop('horses', None)

if 'race_list' not in st.session_state:
    st.info("「レース一覧を取得」を押してください")
    st.stop()

races = st.session_state.race_list
if not races:
    st.warning("レース情報が見つかりませんでした。日付を変えてみてください。")
    st.stop()

# ━━━━━━━ レース選択 ━━━━━━━
labels = [r['label'] for r in races]
selected_label = st.selectbox("レースを選択", labels, label_visibility="collapsed")
selected_race = next(r for r in races if r['label'] == selected_label)

venue = selected_race['venue']
race_no = selected_race['race_no']
st.markdown(f"""
<div style="display:inline-flex;align-items:center;gap:10px;margin:4px 0 12px 0;">
  <div style="background:linear-gradient(135deg,#4a0f2a,#7a1a4a);color:#fff;
              font-weight:bold;padding:6px 16px;border-radius:8px;
              border:1px solid #c8527a;font-size:1rem;">
    {venue}&nbsp;&nbsp;{race_no}R
  </div>
</div>
""", unsafe_allow_html=True)

if st.button("🌸 みことの神託を受け取る", use_container_width=True):
    with st.spinner("みことが解析中...🌸"):
        race_info, horses = jra_scraper.get_race_horses(selected_race['race_id'])
        if horses:
            race_ctx = jra_scraper.parse_race_context(race_info)
            race_id = selected_race['race_id']
            for h in horses:
                my_score = jra_scraper.score_horse(h, horses, race_ctx)
                ext_score = ext.get_external_score(race_id, h['no'])
                h['ext_score'] = ext_score  # 元の外部スコア（表示用）
                h['score'] = ext.blend_score(my_score, ext_score)
            horses_sorted = sorted(horses, key=lambda x: x['score'], reverse=True)
        else:
            horses_sorted = []
        st.session_state.horses = horses_sorted
        st.session_state.race_info = race_info

if 'horses' not in st.session_state:
    st.stop()

horses = st.session_state.horses
race_info = st.session_state.race_info

if not horses:
    st.error("馬データを取得できませんでした。")
    st.stop()

# ━━━━━━━ 印の割り当て ━━━━━━━
def assign_marks(horses):
    marks = {}
    for i, h in enumerate(horses):
        no = h['no']
        if i == 0:
            marks[no] = ('◎', 'mark-hon', '本命')
        elif i == 1:
            marks[no] = ('○', 'mark-tai', '対抗')
        elif i == 2:
            marks[no] = ('▲', 'mark-tan', '単穴')
        elif i in [3, 4]:
            marks[no] = ('△', 'mark-ren', '連下')
        elif i == 5 and h['score'] > -1.0 and h['odds'] > 10:
            marks[no] = ('穴', 'mark-ana', '穴馬')
        else:
            marks[no] = ('　', 'mark-none', '')
    return marks

marks = assign_marks(horses)

# ━━━━━━━ レース評価文生成 ━━━━━━━
def generate_eval(horses, marks, race_info):
    hon = next((h for h in horses if marks[h['no']][0] == '◎'), None)
    tai = next((h for h in horses if marks[h['no']][0] == '○'), None)
    tan = next((h for h in horses if marks[h['no']][0] == '▲'), None)
    ana = next((h for h in horses if marks[h['no']][0] == '穴'), None)

    cond = race_info.get('conditions', '')
    title = race_info.get('title', '')

    lines = []
    lines.append(f"【{race_info.get('race_id','')[:4]}年　{title or selected_label}　みことの神託】")
    lines.append("")

    if hon:
        odds_str = f"（{hon['odds']}倍）" if hon['odds'] > 0 else ""
        lines.append(f"◎ {hon['no']}番 {hon['name']}{odds_str}")
        lines.append(f"　スコア最上位。{hon['jockey']}騎手が手綱を取る注目の一頭。")
        lines.append(f"　今回は素直に本命として狙いたい。")

    if tai:
        lines.append(f"○ {tai['no']}番 {tai['name']}")
        lines.append(f"　対抗は{tai['name']}。本命に次ぐ評価で連軸として有力。")

    if tan:
        lines.append(f"▲ {tan['no']}番 {tan['name']}")
        lines.append(f"　単穴として一発の魅力あり。三連単の３着候補筆頭。")

    if ana:
        lines.append(f"穴 {ana['no']}番 {ana['name']}（{ana['odds']}倍）")
        lines.append(f"　人気薄ながらスコアが底堅い。高配当の鍵を握る存在。")

    lines.append("")
    lines.append("みことの一言：")
    if hon and hon['odds'] > 0 and hon['odds'] <= 3.0:
        lines.append("　「今日は素直に本命から入るのが吉。逆らわないことも大事よ🌸」")
    elif ana:
        lines.append("　「穴馬の気配がするわ。配当に夢を乗せてみて🌸」")
    else:
        lines.append("　「データは揃えたわ。あとはあなたの直感を信じて🌸」")

    return "\n".join(lines)

# ━━━━━━━ 三連単組み合わせ生成 ━━━━━━━
def generate_trifecta(horses, marks):
    hon_horses = [h for h in horses if marks[h['no']][0] == '◎']
    tai_horses = [h for h in horses if marks[h['no']][0] == '○']
    tan_horses = [h for h in horses if marks[h['no']][0] == '▲']
    ren_horses = [h for h in horses if marks[h['no']][0] == '△']
    ana_horses = [h for h in horses if marks[h['no']][0] == '穴']

    combos = []

    # ◎1着固定 → ○▲△穴から2・3着
    second_pool = tai_horses + tan_horses + ren_horses + ana_horses
    if hon_horses and len(second_pool) >= 2:
        h1 = hon_horses[0]
        for h2, h3 in permutations(second_pool[:4], 2):
            combos.append(f"{h1['no']}→{h2['no']}→{h3['no']}")
            if len(combos) >= 6:
                break

    # ◎○の1・2着固定 → ▲△穴から3着
    third_pool = tan_horses + ren_horses + ana_horses
    if hon_horses and tai_horses and third_pool:
        h1, h2 = hon_horses[0], tai_horses[0]
        for h3 in third_pool[:4]:
            combos.append(f"{h1['no']}→{h2['no']}→{h3['no']} ★")

    # ◎軸マルチ（1・2・3着に絡む）
    pool = tai_horses + tan_horses + ren_horses
    if hon_horses and len(pool) >= 2:
        h1 = hon_horses[0]
        for h2, h3 in permutations(pool[:3], 2):
            combos.append(f"{h2['no']}→{h1['no']}→{h3['no']} (マルチ)")
            if len(combos) >= 14:
                break

    return list(dict.fromkeys(combos))[:12]  # 重複除去して最大12点

# ━━━━━━━ 結果表示 ━━━━━━━
st.divider()

ri_title = race_info.get('title', '')
ri_cond = race_info.get('conditions', '')
if ri_title:
    st.markdown(f"### {ri_title}")
if ri_cond:
    st.caption(ri_cond)

# 印凡例
st.markdown("""
<div style="display:flex;gap:16px;margin:8px 0 12px 0;flex-wrap:wrap;">
  <span class="mark-hon">◎ 本命</span>
  <span class="mark-tai">○ 対抗</span>
  <span class="mark-tan">▲ 単穴</span>
  <span class="mark-ren">△ 連下</span>
  <span class="mark-ana">穴 穴馬</span>
</div>
""", unsafe_allow_html=True)

# ヘッダー行
st.markdown("""
<div style="display:grid;grid-template-columns:40px 40px 52px 1fr 70px 70px 160px;
            gap:8px;padding:4px 0;color:#666;font-size:0.75rem;
            border-bottom:1px solid #2a1a2a;margin-bottom:2px;">
  <div style="text-align:center;">印</div>
  <div></div>
  <div style="text-align:center;">馬番</div>
  <div>馬名　騎手</div>
  <div style="text-align:right;">診断点</div>
  <div style="text-align:right;">指数　オッズ</div>
  <div style="padding-left:8px;">-1　0　1　2　3</div>
</div>
""", unsafe_allow_html=True)

min_score = min(h['score'] for h in horses)
max_score = max(h['score'] for h in horses)

for h in horses:
    score = h['score']
    mark, mark_cls, _ = marks[h['no']]
    odds_str = f"{h['odds']}倍" if h['odds'] > 0 else "---"

    if score > 1.0:
        score_cls = "score-pos"
    elif score >= 0:
        score_cls = "score-neu"
    else:
        score_cls = "score-neg"

    # バー
    bar_min, bar_max = -1.0, 3.0
    bar_range = bar_max - bar_min
    zero_pct = int((0 - bar_min) / bar_range * 100)
    score_clamped = max(bar_min, min(bar_max, score))
    score_pct = int((score_clamped - bar_min) / bar_range * 100)

    if score >= 0:
        bar_left = zero_pct
        bar_width = max(score_pct - zero_pct, 2)
        bar_color = "#e8527a" if score > 1.0 else "#7a9acc"
    else:
        bar_left = score_pct
        bar_width = max(zero_pct - score_pct, 2)
        bar_color = "#7a9acc"

    bar_html = f"""
    <div style="position:relative;height:18px;background:#1a0f1f;
                border-radius:9px;overflow:hidden;">
      <div style="position:absolute;left:{bar_left}%;width:{bar_width}%;
                  height:100%;background:{bar_color};border-radius:9px;"></div>
    </div>"""

    ext_score = h.get('ext_score')
    ext_str = f"{ext_score:.1f}" if ext_score is not None else "—"
    ext_color = "#ff8fab" if ext_score and ext_score >= 80 else ("#ffcc66" if ext_score and ext_score >= 60 else "#888")

    st.markdown(f"""
    <div style="display:grid;grid-template-columns:40px 40px 52px 1fr 70px 70px 160px;
                align-items:center;gap:8px;padding:7px 0;
                border-bottom:1px solid #1a0f1f;">
      <div style="text-align:center;" class="{mark_cls}">{mark}</div>
      <div></div>
      <div style="text-align:center;font-weight:bold;color:#f0e0f0;font-size:1rem;">{h['no']}</div>
      <div>
        <div style="font-weight:bold;color:#fff;font-size:0.95rem;">{h['name']}</div>
        <div style="font-size:0.75rem;color:#c090a0;">{h['jockey']}</div>
      </div>
      <div style="text-align:right;">
        <div style="color:{ext_color};font-weight:bold;font-size:0.9rem;">{ext_str}</div>
      </div>
      <div style="text-align:right;">
        <div class="{score_cls}">{score:.3f}</div>
        <div style="font-size:0.75rem;color:#886070;">{odds_str}</div>
      </div>
      <div style="padding-left:8px;">{bar_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ━━━━━━━ 三連単予想 ━━━━━━━
col_tri, col_eval = st.columns([1, 1])

with col_tri:
    st.markdown('<div class="trifecta-title">🎯 三連単　みこと厳選フォーメーション</div>', unsafe_allow_html=True)
    combos = generate_trifecta(horses, marks)
    if combos:
        combo_html = "<br>".join(combos)
        st.markdown(f'<div class="trifecta-box"><div class="trifecta-combo">{combo_html}</div></div>', unsafe_allow_html=True)
        st.caption(f"合計 {len(combos)} 点")
    else:
        st.info("頭数が少なく三連単を組めませんでした")

with col_eval:
    st.markdown('<div class="trifecta-title">🌸 みことの神託　レース評価</div>', unsafe_allow_html=True)
    eval_text = generate_eval(horses, marks, race_info)
    st.markdown(f'<div class="eval-box"><pre style="white-space:pre-wrap;font-family:inherit;margin:0;">{eval_text}</pre></div>', unsafe_allow_html=True)

st.divider()
st.caption("※ スコアは簡易ロジックによる参考値です。オッズ未公開時は精度が下がります。")
st.caption("🌸 uma姫AI 予想ビルダー　powered by みこと")
