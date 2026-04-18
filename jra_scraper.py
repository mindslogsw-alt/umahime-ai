import requests
from bs4 import BeautifulSoup
import re
from datetime import date

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

VENUE_MAP = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉'
}

def get_race_list(target_date: date) -> list[dict]:
    """指定日のJRAレース一覧を返す [{venue, race_no, race_id, race_name}]"""
    date_str = target_date.strftime('%Y%m%d')
    url = f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date_str}'
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'EUC-JP'
    except Exception:
        return []

    soup = BeautifulSoup(res.text, 'html.parser')
    races = []

    for dl in soup.find_all('dl', class_='RaceList_DataList'):
        dt = dl.find('dt')
        venue_text = dt.text.strip() if dt else ''

        for a in dl.find_all('a', href=True):
            if 'shutuba' not in a['href']:
                continue
            m = re.search(r'race_id=(\w+)', a['href'])
            if not m:
                continue
            race_id = m.group(1)
            race_no = str(int(race_id[-2:]))  # race_idの末尾2桁がレース番号
            venue_code = race_id[4:6]
            venue = VENUE_MAP.get(venue_code, venue_text)
            races.append({
                'venue': venue,
                'race_no': race_no,
                'race_id': race_id,
                'label': f'{venue} {race_no}R',
            })

    return sorted(races, key=lambda x: (x['venue'], int(x['race_no']) if x['race_no'].isdigit() else 0))


def get_odds(race_id: str) -> dict[int, float]:
    """netkeibaオッズAPIから単勝オッズを取得して {馬番: オッズ} で返す"""
    url = f'https://race.netkeiba.com/api/api_get_jra_odds.html?race_id={race_id}&type=1&action=update'
    headers = {**HEADERS, 'Referer': f'https://race.netkeiba.com/odds/index.html?race_id={race_id}'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        odds_raw = data['data']['odds']['1']
        return {int(k): float(v[0]) for k, v in odds_raw.items() if v[0] not in ('', '---')}
    except Exception:
        return {}


def get_race_horses(race_id: str) -> tuple[dict, list[dict]]:
    """出馬表を取得して (レース情報, 馬リスト) を返す"""
    url = f'https://race.netkeiba.com/race/shutuba.html?race_id={race_id}'
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'EUC-JP'
    except Exception:
        return {}, []

    soup = BeautifulSoup(res.text, 'html.parser')

    # レース情報
    race_info = {'race_id': race_id, 'title': '', 'conditions': ''}
    title_el = soup.find('div', class_='RaceName')
    if title_el:
        race_info['title'] = title_el.text.strip()
    cond_el = soup.find('div', class_='RaceData01')
    if cond_el:
        race_info['conditions'] = cond_el.text.strip().replace('\n', ' ')

    table = soup.find('table', class_='Shutuba_Table')
    if not table:
        return race_info, []

    horses = []
    for row in table.find_all('tr'):
        tds = row.find_all('td')
        if len(tds) < 7:
            continue
        try:
            bracket = int(tds[0].text.strip()) if tds[0].text.strip().isdigit() else 0
            no = int(tds[1].text.strip()) if tds[1].text.strip().isdigit() else 0
            if no == 0:
                continue
            name = tds[3].text.strip()
            sex_age = tds[4].text.strip() if len(tds) > 4 else ''
            weight_carry = float(tds[5].text.strip()) if len(tds) > 5 and tds[5].text.strip().replace('.','').isdigit() else 0
            jockey = tds[6].text.strip() if len(tds) > 6 else ''

            # 馬体重・増減
            body_weight_text = tds[8].text.strip() if len(tds) > 8 else ''
            body_weight, weight_change = 0, 0
            wm = re.search(r'(\d+)\(([+-]?\d+)\)', body_weight_text)
            if wm:
                body_weight = int(wm.group(1))
                weight_change = int(wm.group(2))

            # 単勝オッズ
            odds_text = tds[10].text.strip() if len(tds) > 10 else ''
            try:
                odds = float(odds_text)
            except ValueError:
                odds = 0.0

            horses.append({
                'bracket': bracket,
                'no': no,
                'name': name,
                'sex_age': sex_age,
                'weight_carry': weight_carry,
                'jockey': jockey,
                'body_weight': body_weight,
                'weight_change': weight_change,
                'odds': odds,
            })
        except (ValueError, IndexError):
            continue

    # オッズAPIで上書き
    odds_map = get_odds(race_id)
    if odds_map:
        for h in horses:
            h['odds'] = odds_map.get(h['no'], h['odds'])

    return race_info, horses


def parse_race_context(race_info: dict) -> dict:
    """レース情報テキストからコース・距離・馬場を解析する"""
    cond = race_info.get('conditions', '')
    race_id = race_info.get('race_id', '')

    is_dirt = 'ダ' in cond or 'ダート' in cond
    is_turf = '芝' in cond and not is_dirt

    # 距離を抽出 (例: "芝1600m")
    import re as _re
    dist_m = _re.search(r'(\d{3,4})m', cond)
    distance = int(dist_m.group(1)) if dist_m else 0

    # 場コードから競馬場を特定
    venue_code = race_id[4:6] if len(race_id) >= 6 else '00'

    # 馬場状態（良/稍重/重/不良）
    track_cond = '良'
    for c in ['不良', '重', '稍重', '良']:
        if c in cond:
            track_cond = c
            break

    return {
        'is_dirt': is_dirt,
        'is_turf': is_turf,
        'distance': distance,
        'venue_code': venue_code,
        'track_cond': track_cond,
    }


def score_horse(horse: dict, all_horses: list[dict], race_ctx: dict | None = None) -> float:
    """
    NotebookLMロジック反映スコアリング（-3〜+3スケール）

    理論根拠（ウマキング・KARINA・地方定量スコア）:
    - 期待値 = 想定勝率 × オッズ > 100% を狙う
    - 枠順バイアス: 芝=内前有利、ダート=外枠有利（例外あり）
    - 大型馬(480-520kg) × 中穴(7-15倍) = 地方ダートの旨味ゾーン
    - 危険な過剰人気馬(1.5倍以下)は減点
    - 100倍超は原則切り
    """
    score = 0.0

    valid_odds = [h['odds'] for h in all_horses if h['odds'] > 0]
    if not valid_odds:
        return 0.0

    odds = horse['odds']
    if odds <= 0:
        return -1.5

    ctx = race_ctx or {}
    is_dirt = ctx.get('is_dirt', False)
    is_turf = ctx.get('is_turf', True)
    distance = ctx.get('distance', 0)
    venue_code = ctx.get('venue_code', '00')
    track_cond = ctx.get('track_cond', '良')
    bracket = horse.get('bracket', 0)
    body_weight = horse.get('body_weight', 0)
    weight_change = horse.get('weight_change', 0)

    # ━━━ 期待値ロジック ━━━
    # 最低人気の1倍台は過剰人気 → 期待値が低い
    if odds <= 1.5:
        score -= 0.8
    elif odds <= 3.0:
        score += 0.3
    elif odds <= 8.0:
        score += 0.6
    elif 8.0 < odds <= 15.0:
        score += 1.0   # 期待値の塊ゾーン（上位候補）
    elif 15.0 < odds <= 50.0:
        score += 0.8   # 穴馬ゾーン
    elif 50.0 < odds <= 100.0:
        score -= 0.5
    else:
        score -= 1.5   # 100倍超は原則切り

    # ━━━ 枠順バイアス ━━━
    if is_turf:
        # 芝: 内前有利（開幕週想定）
        if bracket in [1, 2]:
            score += 0.6
        elif bracket in [3, 4]:
            score += 0.2
        elif bracket in [7, 8]:
            score -= 0.4

        # 東京芝: 直線が長くバイアス緩和、外枠のマイナス小さい
        if venue_code == '05':
            if bracket in [7, 8]:
                score += 0.2  # 補正で戻す

        # 中山: 小回り・先行有利
        if venue_code == '06' and bracket in [1, 2, 3]:
            score += 0.3

    elif is_dirt:
        # ダート: 外枠有利（砂被り回避）
        if bracket in [7, 8]:
            score += 0.5
        elif bracket in [1, 2]:
            score -= 0.4

        # 東京ダート1600m: 芝スタートで外枠が最も有利
        if venue_code == '05' and distance == 1600:
            if bracket in [7, 8]:
                score += 0.5   # さらに加点
            elif bracket in [1, 2]:
                score -= 0.3   # さらに減点

        # 阪神ダート: 大箱で外有利が最大
        if venue_code == '09' and is_dirt:
            if bracket in [7, 8]:
                score += 0.3

        # 京都ダート1800m: 例外的に内枠有利（下り坂スタート）
        if venue_code == '08' and distance == 1800:
            if bracket in [1, 2]:
                score += 0.5
            elif bracket in [7, 8]:
                score -= 0.3

    # ━━━ 馬体重・パワー補正（ダート） ━━━
    if is_dirt and body_weight > 0:
        if 480 <= body_weight <= 520:
            score += 0.4   # 大型馬ダート有利
        elif body_weight < 450:
            score -= 0.5   # 小型馬はダートで不利

    # 馬体重の急増減は不安材料
    if body_weight > 0 and abs(weight_change) >= 20:
        score -= 0.4

    # 道悪（重・不良）では大型馬がさらに有利
    if track_cond in ['重', '不良'] and is_dirt and body_weight >= 500:
        score += 0.3

    # ━━━ スケール正規化 ━━━
    score = max(-3.0, min(3.0, score))
    return round(score, 3)
