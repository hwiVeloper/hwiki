#!/usr/bin/env python3
"""
KBO 경기 결과 자동 수집 스크립트
koreabaseball.com 공식 API를 사용해 이닝별 상세 데이터 포함 경기 결과를 수집합니다.

사용법:
    python scripts/kbo_scraper.py              # 전날 경기 수집 (KST 기준)
    python scripts/kbo_scraper.py 20260408     # 특정 날짜 수집
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR  = os.path.join(BASE_DIR, "raw", "articles", "kbo", "2026")

KBO = "https://www.koreabaseball.com"
API_GAMELIST   = KBO + "/ws/Main.asmx/GetKboGameList"
API_SCOREBOARD = KBO + "/ws/Schedule.asmx/GetScoreBoardScroll"
API_BOXSCORE   = KBO + "/ws/Schedule.asmx/GetBoxScoreScroll"

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": KBO + "/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

# KBO 내부 팀코드 매핑
TEAM_CODE_KR = {
    "HT": "KIA",  "SK": "SSG",  "KT": "KT",   "LG": "LG",
    "LT": "롯데", "SS": "삼성", "OB": "두산", "NC": "NC",
    "WO": "키움", "HH": "한화",
}
TEAM_CODE_EN = {
    "HT": "kia",  "SK": "ssg",  "KT": "kt",   "LG": "lg",
    "LT": "lotte","SS": "samsung","OB": "doosan","NC": "nc",
    "WO": "kiwoom","HH": "hanwha",
}


def post(url: str, data: dict) -> dict:
    resp = requests.post(url, data=data, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def rows_texts(table_json: str) -> list[list[str]]:
    """JSON 테이블 문자열 → [[셀텍스트, ...], ...] 변환."""
    t = json.loads(table_json)
    result = []
    for row in t.get("rows", []):
        cells = []
        for c in row.get("row", []):
            text = c["Text"].strip()
            text = "" if text in ("&nbsp;", "\xa0") else text
            cells.append(text)
        result.append(cells)
    return result


# ──────────────────────────────────────────────
# 1. 날짜별 경기 ID 목록
# ──────────────────────────────────────────────

def get_game_ids(date_str: str) -> list[dict]:
    """특정 날짜의 완료된 경기 목록 반환.

    Returns:
        [{"game_id": "20260408SSHT0", "away_id": "SS", "home_id": "HT",
          "away_nm": "삼성", "home_nm": "KIA", "away_score": 5, "home_score": 15,
          "winner": "최민석", "loser": "이승현", "save": ""}, ...]
    """
    data = post(API_GAMELIST, {"leId": "1", "srId": "0", "date": date_str})
    games = []
    for g in data.get("game", []):
        # GAME_RESULT_CK=1: 경기 완료
        if str(g.get("GAME_RESULT_CK", "0")) != "1":
            continue
        # 정상 경기만 (우천취소 등 제외)
        if str(g.get("CANCEL_SC_ID", "0")) != "0":
            continue
        games.append({
            "game_id":    g["G_ID"],
            "away_id":    g["AWAY_ID"],
            "home_id":    g["HOME_ID"],
            "away_nm":    g["AWAY_NM"],
            "home_nm":    g["HOME_NM"],
            "away_score": int(g.get("T_SCORE_CN", 0)),
            "home_score": int(g.get("B_SCORE_CN", 0)),
            "winner":     g.get("W_PIT_P_NM", "").strip(),
            "loser":      g.get("L_PIT_P_NM", "").strip(),
            "save":       g.get("SV_PIT_P_NM", "").strip(),
        })
    return games


# ──────────────────────────────────────────────
# 2. 스코어보드 + 메타데이터
# ──────────────────────────────────────────────

def get_scoreboard(game_id: str, season_id: str) -> dict:
    """구장·관중·시간 + 이닝별 스코어 반환."""
    params = {"leId": "1", "srId": "0", "seasonId": season_id, "gameId": game_id}
    d = post(API_SCOREBOARD, params)

    # 이닝 스코어 (table2: 원정, 홈 × 12이닝)
    inn_rows = rows_texts(d["table2"])   # [[이닝1..12 원정], [이닝1..12 홈]]
    # R H E B (table3)
    rheb_rows = rows_texts(d["table3"])  # [[R H E B 원정], [R H E B 홈]]

    return {
        "stadium":    d.get("S_NM", ""),
        "attendance": d.get("CROWD_CN", ""),
        "start_time": d.get("START_TM", ""),
        "end_time":   d.get("END_TM", ""),
        "duration":   d.get("USE_TM", ""),
        "inn_away":   inn_rows[0] if inn_rows else [],
        "inn_home":   inn_rows[1] if len(inn_rows) > 1 else [],
        "rheb_away":  rheb_rows[0] if rheb_rows else [],
        "rheb_home":  rheb_rows[1] if len(rheb_rows) > 1 else [],
    }


# ──────────────────────────────────────────────
# 3. 타자·투수·주요기록
# ──────────────────────────────────────────────

def get_boxscore(game_id: str, season_id: str) -> dict:
    """이닝별 타자 결과 + 투수 기록 + 주요기록 반환."""
    params = {"leId": "1", "srId": "0", "seasonId": season_id, "gameId": game_id}
    d = post(API_BOXSCORE, params)

    # 타자 (arrHitter[0]=원정, [1]=홈)
    batters = []
    for hitter_team in d.get("arrHitter", []):
        t1 = rows_texts(hitter_team["table1"])  # [[타순, 포지션, 이름], ...]
        t2 = rows_texts(hitter_team["table2"])  # [[1회, 2회, ..., N회], ...]
        t3 = rows_texts(hitter_team["table3"])  # [[타수, 안타, 타점, 득점, 타율], ...]
        team_batters = []
        for i, info in enumerate(t1):
            if len(info) < 3:
                continue
            inn_vals = t2[i] if i < len(t2) else []
            stats    = t3[i] if i < len(t3) else []
            team_batters.append({
                "order": info[0],
                "pos":   info[1],
                "name":  info[2],
                "inn":   inn_vals,   # 최대 9개 이닝 결과
                "ab":    stats[0] if len(stats) > 0 else "",
                "h":     stats[1] if len(stats) > 1 else "",
                "rbi":   stats[2] if len(stats) > 2 else "",
                "r":     stats[3] if len(stats) > 3 else "",
                "avg":   stats[4] if len(stats) > 4 else "",
            })
        batters.append(team_batters)

    # 투수 (arrPitcher[0]=원정, [1]=홈)
    # row: [이름, 등판, 결과, 승, 패, 세, 이닝, 타자, 투구수, 타수, 피안타, 홈런, 4사구, 삼진, 실점, 자책, ERA]
    pitchers = []
    for pitcher_team in d.get("arrPitcher", []):
        rows = rows_texts(pitcher_team["table"])
        team_pitchers = []
        for row in rows:
            if len(row) < 2 or row[0] in ("TOTAL", "합계", ""):
                continue
            team_pitchers.append({
                "name":   row[0]  if len(row) > 0  else "",
                "debut":  row[1]  if len(row) > 1  else "",
                "result": row[2]  if len(row) > 2  else "",
                "win":    row[3]  if len(row) > 3  else "0",
                "lose":   row[4]  if len(row) > 4  else "0",
                "save":   row[5]  if len(row) > 5  else "0",
                "ip":     row[6]  if len(row) > 6  else "0",
                "bf":     row[7]  if len(row) > 7  else "0",
                "np":     row[8]  if len(row) > 8  else "0",
                "ab":     row[9]  if len(row) > 9  else "0",
                "h":      row[10] if len(row) > 10 else "0",
                "hr":     row[11] if len(row) > 11 else "0",
                "bb":     row[12] if len(row) > 12 else "0",
                "so":     row[13] if len(row) > 13 else "0",
                "er_r":   row[14] if len(row) > 14 else "0",
                "er":     row[15] if len(row) > 15 else "0",
                "era":    row[16] if len(row) > 16 else "0.00",
            })
        pitchers.append(team_pitchers)

    # 주요기록 (tableEtc)
    key_records = []
    for row in rows_texts(d["tableEtc"]):
        if len(row) >= 2 and row[0] and row[1]:
            val = row[1].replace("\r\n", "").strip()
            key_records.append((row[0], val))

    return {
        "batters_away":  batters[0] if batters else [],
        "batters_home":  batters[1] if len(batters) > 1 else [],
        "pitchers_away": pitchers[0] if pitchers else [],
        "pitchers_home": pitchers[1] if len(pitchers) > 1 else [],
        "key_records":   key_records,  # [("홈런", "김도영2호(...)"), ...]
        "max_inning":    d.get("maxInning", 9),
    }


# ──────────────────────────────────────────────
# 4. 마크다운 생성
# ──────────────────────────────────────────────

def format_markdown(game_meta: dict, board: dict, box: dict) -> str:
    away_nm = game_meta["away_nm"]
    home_nm = game_meta["home_nm"]
    away_sc = game_meta["away_score"]
    home_sc = game_meta["home_score"]
    gid     = game_meta["game_id"]

    date_str = gid[:8]
    y, m, d  = date_str[:4], date_str[4:6], date_str[6:]
    date_display = f"{y}년 {int(m)}월 {int(d)}일"

    lines = [
        f"# {away_nm} {away_sc} vs {home_sc} {home_nm}",
        "",
        f"- **날짜**: {date_display}",
        f"- **경기 ID**: {gid}",
        f"- **구장**: {board['stadium']}",
        f"- **관중**: {board['attendance']}",
        f"- **개시**: {board['start_time']}",
        f"- **종료**: {board['end_time']}",
        f"- **경기시간**: {board['duration']}",
        "",
    ]

    # ── 스코어보드 ──
    lines.append("## 스코어보드")
    lines.append("| 팀 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | R | H | E | B |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    for team_nm, inn, rheb in [
        (away_nm, board["inn_away"], board["rheb_away"]),
        (home_nm, board["inn_home"], board["rheb_home"]),
    ]:
        padded = (inn + ["-"] * 12)[:12]
        r = rheb[0] if rheb else "-"
        h = rheb[1] if len(rheb) > 1 else "-"
        e = rheb[2] if len(rheb) > 2 else "-"
        b = rheb[3] if len(rheb) > 3 else "-"
        inn_str = " | ".join(padded)
        lines.append(f"| {team_nm} | {inn_str} | {r} | {h} | {e} | {b} |")

    lines.append("")

    # ── 주요 기록 ──
    lines.append("## 주요 기록")
    if box["key_records"]:
        for label, val in box["key_records"]:
            lines.append(f"- **{label}**: {val}")
    else:
        lines.append("- (기록 없음)")
    lines.append("")

    # ── 타자 기록 ──
    for team_nm, batters in [(away_nm, box["batters_away"]), (home_nm, box["batters_home"])]:
        lines.append(f"## {team_nm} 타자 기록")
        lines.append("| 타순 | 포지션 | 선수명 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 타수 | 안타 | 타점 | 득점 | 타율 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for b in batters:
            inn9 = (b["inn"] + [""] * 9)[:9]
            inn_str = " | ".join(inn9)
            lines.append(
                f"| {b['order']} | {b['pos']} | {b['name']} | "
                f"{inn_str} | "
                f"{b['ab']} | {b['h']} | {b['rbi']} | {b['r']} | {b['avg']} |"
            )
        lines.append("")

    # ── 투수 기록 ──
    for team_nm, pitchers in [(away_nm, box["pitchers_away"]), (home_nm, box["pitchers_home"])]:
        lines.append(f"## {team_nm} 투수 기록")
        lines.append("| 선수명 | 등판 | 결과 | 승 | 패 | 세 | 이닝 | 타자 | 투구수 | 타수 | 피안타 | 홈런 | 4사구 | 삼진 | 실점 | 자책 | 평균자책점 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for p in pitchers:
            lines.append(
                f"| {p['name']} | {p['debut']} | {p['result']} | "
                f"{p['win']} | {p['lose']} | {p['save']} | {p['ip']} | "
                f"{p['bf']} | {p['np']} | {p['ab']} | {p['h']} | "
                f"{p['hr']} | {p['bb']} | {p['so']} | {p['er_r']} | {p['er']} | {p['era']} |"
            )
        lines.append("")

    # ── 경기 결과 ──
    lines.append("## 경기 결과")
    lines.append(f"- **승리 투수**: {game_meta['winner']}")
    lines.append(f"- **패전 투수**: {game_meta['loser']}")
    if game_meta["save"]:
        lines.append(f"- **세이브**: {game_meta['save']}")
    lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 5. 파일 저장
# ──────────────────────────────────────────────

def save_game(game_id: str, away_nm: str, home_nm: str, content: str) -> bool:
    date_str = game_id[:8]
    out_dir  = os.path.join(RAW_DIR, date_str)
    os.makedirs(out_dir, exist_ok=True)

    filename = f"{game_id}_{away_nm}_vs_{home_nm}.md"
    filepath = os.path.join(out_dir, filename)

    if os.path.exists(filepath):
        print(f"  [SKIP] 이미 존재: {filename}")
        return False

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [SAVE] {filename}")
    return True


# ──────────────────────────────────────────────
# 6. 메인
# ──────────────────────────────────────────────

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and re.match(r"\d{8}", args[0]):
        date_str = args[0]
    else:
        date_str = (datetime.now(KST) - timedelta(days=1)).strftime("%Y%m%d")

    season_id = date_str[:4]
    print(f"[KBO Scraper] 수집 대상: {date_str}")

    # 1) 경기 목록
    try:
        games = get_game_ids(date_str)
    except Exception as e:
        print(f"[ERROR] 경기 목록 조회 실패: {e}")
        sys.exit(1)

    if not games:
        print(f"[KBO Scraper] {date_str} 완료된 경기 없음")
        return

    print(f"[KBO Scraper] {len(games)}경기 발견: {[g['game_id'] for g in games]}")

    saved = 0
    for g in games:
        gid = g["game_id"]
        print(f"  → {gid} ({g['away_nm']} vs {g['home_nm']}) 수집 중...")
        try:
            board = get_scoreboard(gid, season_id)
            box   = get_boxscore(gid, season_id)
            md    = format_markdown(g, board, box)
            if save_game(gid, g["away_nm"], g["home_nm"], md):
                saved += 1
        except Exception as e:
            print(f"  [ERROR] {gid}: {e}")

    print(f"\n[KBO Scraper] 완료: {saved}/{len(games)} 저장")

    if saved > 0:
        print("[KBO Scraper] rebuild_kbo_wiki.py 실행 중...")
        os.system(f"python3 {os.path.join(BASE_DIR, 'scripts', 'rebuild_kbo_wiki.py')}")


if __name__ == "__main__":
    main()
