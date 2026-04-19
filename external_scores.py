# 外部診断スコア（全頭診断ロジックより）
# スケール: 0〜100点

EXTERNAL_SCORES = {
    # 皐月賞 2026 (202606030811)
    "202606030811": {
        1:  85.5,  # カヴァレリッツォ
        2:  72.2,  # サウンドムーブ
        3:  50.4,  # サノノグレーター
        4:  81.0,  # ロブチェン
        5:  41.1,  # アスクエジンバラ
        6:  44.5,  # フォルテアンジェロ
        7:  14.8,  # ロードフィレール
        8:  88.1,  # マテンロウゲイル
        9:  61.4,  # ライヒスアドラー
        10:  8.6,  # ラージアンサンブル
        11: 58.9,  # パントルナイーフ
        12: 86.9,  # グリーンエナジー
        13: 55.5,  # アクロフェイズ
        14: 75.2,  # ゾロアストロ
        15: 87.0,  # リアライズシリウス
        16: 42.0,  # アルトラムス
        17: 83.2,  # アドマイヤクワッズ
        18: 67.7,  # バステール
    }
}


def get_external_score(race_id: str, horse_no: int) -> float | None:
    """外部スコアを返す。なければNone"""
    return EXTERNAL_SCORES.get(race_id, {}).get(horse_no)


def normalize_external(score: float) -> float:
    """0〜100スケールを -3〜+3 に変換"""
    return round((score - 50) / 50 * 3, 3)


def blend_score(my_score: float, ext_score: float | None, weight: float = 0.6) -> float:
    """外部スコアとブレンド（外部スコアをweight割で優先）"""
    if ext_score is None:
        return my_score
    ext_norm = normalize_external(ext_score)
    blended = my_score * (1 - weight) + ext_norm * weight
    return round(max(-3.0, min(3.0, blended)), 3)
