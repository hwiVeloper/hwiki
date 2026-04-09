#!/usr/bin/env python3
"""
KBO 경기 결과 자동 수집 스크립트 (Playwright 기반)
KBO 공식 게임센터(kbo.or.kr)에서 이닝별 상세 데이터를 포함한 경기 결과를 수집합니다.

사용법:
    python scripts/kbo_scraper.py              # 전날 경기 수집
    python scripts/kbo_scraper.py 20260408     # 특정 날짜 수집
    python scripts/kbo_scraper.py --debug      # 캡처된 API 응답 덤프
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR  = os.path.join(BASE_DIR, "raw", "articles", "kbo", "2026")

KBO_BASE     = "https://www.kbo.or.kr"
# 아래 URL은 KBO 사이트 변경 시 수정 필요
# 브라우저 개발자도구 Network 탭에서 실제 요청 URL을 확인하세요
SCHEDULE_URL = KBO_BASE + "/schedule/index"
GAME_URL     = KBO_BASE + "/game/kboGame/gameCenter"

# 대체 일정 URL 후보 (실패 시 순서대로 시도)
SCHEDULE_URLS = [
    KBO_BASE + "/schedule/index?gameDate={date}",
    KBO_BASE + "/schedule/index?srId=gameRecord&seasonId={year}&gameDate={date}",
    KBO_BASE + "/schedule/list?gameDate={date}",
]

DEBUG = "--debug" in sys.argv

# KBO 내부 팀코드 → 한국어/영문 매핑
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
TEAM_FULL = {
    "KIA": "KIA 타이거즈", "SSG": "SSG 랜더스", "KT": "KT 위즈",
    "LG": "LG 트윈스",   "롯데": "롯데 자이언츠","삼성": "삼성 라이온즈",
    "두산": "두산 베어스","NC": "NC 다이노스",
    "키움": "키움 히어로즈","한화": "한화 이글스",
}


# ──────────────────────────────────────────────
# 1. 날짜별 경기 ID 목록 수집
# ──────────────────────────────────────────────

async def get_game_ids(page, date_str: str) -> list[str]:
    """KBO 일정 페이지에서 해당 날짜 경기 ID 목록 반환.

    실패 시 확인사항:
    - SCHEDULE_URLS 상수에서 올바른 URL 패턴 확인
    - 브라우저 개발자도구 → Network → kbo.or.kr 요청 중 gameId 포함된 URL 찾기
    """
    captured = {}

    async def on_response(resp):
        url = resp.url
        if KBO_BASE in url and resp.status == 200:
            try:
                data = await resp.json()
                captured[url] = data
            except Exception:
                pass

    page.on("response", on_response)

    year = date_str[:4]
    game_ids = []

    # 여러 URL 패턴 순서대로 시도
    for url_template in SCHEDULE_URLS:
        target_url = url_template.format(date=date_str, year=year)
        try:
            await page.goto(target_url, wait_until="networkidle", timeout=30000)

            # API 응답에서 gameId 추출
            for url, data in captured.items():
                _extract_game_ids_from_json(data, game_ids)

            # API가 잡히지 않으면 DOM에서 추출 (fallback)
            if not game_ids:
                content = await page.content()
                found = re.findall(rf"{date_str}[A-Z]{{4}}\d", content)
                game_ids = list(dict.fromkeys(found))

            if game_ids:
                if DEBUG:
                    print(f"[DEBUG] 성공한 일정 URL: {target_url}")
                break

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] URL 실패 ({target_url}): {e}")
            continue

    if DEBUG:
        print(f"[DEBUG] {date_str} 경기 ID: {game_ids}")
        print(f"[DEBUG] 캡처된 API URL 목록:")
        for url in captured.keys():
            print(f"  - {url}")

    return game_ids


def _extract_game_ids_from_json(data, result: list):
    """JSON 응답에서 재귀적으로 gameId 추출."""
    if isinstance(data, dict):
        if "gameId" in data:
            gid = str(data["gameId"])
            if re.match(r"\d{8}[A-Z]{4}\d", gid) and gid not in result:
                result.append(gid)
        for v in data.values():
            _extract_game_ids_from_json(v, result)
    elif isinstance(data, list):
        for item in data:
            _extract_game_ids_from_json(item, result)


# ──────────────────────────────────────────────
# 2. 경기 데이터 수집
# ──────────────────────────────────────────────

async def get_game_data(page, game_id: str) -> dict | None:
    """게임센터 API를 인터셉트해 경기 전체 데이터 수집."""
    captured = {}

    async def on_response(resp):
        url = resp.url
        if KBO_BASE in url and resp.status == 200:
            try:
                data = await resp.json()
                captured[url] = data
            except Exception:
                pass

    page.on("response", on_response)
    await page.goto(f"{GAME_URL}?gameId={game_id}", wait_until="networkidle", timeout=30000)

    if DEBUG:
        dump_path = os.path.join(BASE_DIR, f"debug_{game_id}.json")
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in captured.items()}, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] API 덤프 저장: {dump_path}")

    return _build_game(game_id, captured)


def _build_game(game_id: str, captured: dict) -> dict | None:
    """캡처된 API 응답들을 파싱해 통합 game dict 반환."""
    date_str  = game_id[:8]
    home_code = game_id[8:10]
    away_code = game_id[10:12]

    game = {
        "game_id":       game_id,
        "date_str":      date_str,           # "20260408"
        "home_kr":       TEAM_CODE_KR.get(home_code, home_code),
        "away_kr":       TEAM_CODE_KR.get(away_code, away_code),
        "home_en":       TEAM_CODE_EN.get(home_code, home_code.lower()),
        "away_en":       TEAM_CODE_EN.get(away_code, away_code.lower()),
        "home_score":    0,
        "away_score":    0,
        "stadium":       "",
        "attendance":    "",
        "start_time":    "",
        "end_time":      "",
        "duration":      "",
        "scoreboard":    [],   # [[팀, 1, 2, ..., R, H, E, B], ...]
        "key_records":   [],   # ["결승타: ...", "홈런: ...", ...]
        "away_batters":  [],   # 타자 행 리스트
        "home_batters":  [],
        "away_pitchers": [],   # 투수 행 리스트
        "home_pitchers": [],
        "winner":        "",
        "loser":         "",
        "save":          "",
    }

    for url, data in captured.items():
        url_lower = url.lower()
        try:
            # 기본 경기 정보
            if any(k in url_lower for k in ["schedule", "gameinfo", "summary"]):
                _parse_game_info(data, game)

            # 타자 기록
            if any(k in url_lower for k in ["bat", "hitter", "batter"]):
                _parse_batter_data(data, game)

            # 투수 기록
            if any(k in url_lower for k in ["pit", "pitcher"]):
                _parse_pitcher_data(data, game)

            # 주요 기록 / 특기사항
            if any(k in url_lower for k in ["note", "special", "record", "remark"]):
                _parse_key_records(data, game)

            # 스코어보드
            if any(k in url_lower for k in ["score", "inning", "board"]):
                _parse_scoreboard(data, game)

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] 파싱 오류 ({url}): {e}")

    return game if (game["home_score"] or game["away_score"]) else None


def _get_val(data, *keys, default=""):
    """중첩 dict에서 키를 순서대로 탐색."""
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data if data is not None else default


def _parse_game_info(data: dict, game: dict):
    flat = _flatten(data)
    for key, val in flat.items():
        kl = key.lower()
        if "stadium" in kl or "stadium" in kl or "구장" in kl:
            game["stadium"] = game["stadium"] or str(val)
        elif "crowd" in kl or "attendance" in kl or "관중" in kl:
            game["attendance"] = game["attendance"] or str(val)
        elif "starttime" in kl or "개시" in kl:
            game["start_time"] = game["start_time"] or str(val)
        elif "endtime" in kl or "종료" in kl:
            game["end_time"] = game["end_time"] or str(val)
        elif "gametime" in kl or "경기시간" in kl:
            game["duration"] = game["duration"] or str(val)
        elif "homeScore" in key or "homeTotalScore" in key:
            game["home_score"] = game["home_score"] or int(val)
        elif "awayScore" in key or "awayTotalScore" in key:
            game["away_score"] = game["away_score"] or int(val)
        elif "winPitcher" in key or "승리투수" in key:
            game["winner"] = game["winner"] or str(val)
        elif "losePitcher" in key or "패전투수" in key:
            game["loser"] = game["loser"] or str(val)
        elif "savePitcher" in key or "세이브" in key:
            game["save"] = game["save"] or str(val)


def _parse_scoreboard(data: dict, game: dict):
    """이닝별 스코어 파싱. data에 inningScores 또는 scoreboard 키가 있을 것으로 예상."""
    if not game["scoreboard"]:
        # 흔히 쓰이는 키 패턴들 시도
        for key in ["inningScores", "scoreBoard", "innings", "innScore"]:
            board = _get_val(data, key)
            if board and isinstance(board, list):
                for row in board:
                    if isinstance(row, dict):
                        scores = [row.get(f"i{i}", "-") for i in range(1, 13)]
                        team = row.get("teamName", row.get("team", ""))
                        r = row.get("run", row.get("r", ""))
                        h = row.get("hit", row.get("h", ""))
                        e = row.get("error", row.get("e", ""))
                        b = row.get("ball", row.get("b", ""))
                        game["scoreboard"].append([team] + scores + [r, h, e, b])
                break


def _parse_batter_data(data: dict, game: dict):
    """타자 기록 파싱 (이닝별 결과 포함)."""
    rows_away, rows_home = [], []

    # 공통 패턴: {"away": [...], "home": [...]} 또는 {"batters": [...]}
    away_list = _find_list(data, ["away", "awayBatters", "visitorBatters"])
    home_list = _find_list(data, ["home", "homeBatters"])

    for batter in (away_list or []):
        rows_away.append(_parse_batter_row(batter))
    for batter in (home_list or []):
        rows_home.append(_parse_batter_row(batter))

    if rows_away and not game["away_batters"]:
        game["away_batters"] = rows_away
    if rows_home and not game["home_batters"]:
        game["home_batters"] = rows_home


def _parse_batter_row(b: dict) -> dict:
    """타자 한 행 파싱."""
    inning_results = {}
    for i in range(1, 13):
        v = b.get(f"inn{i}", b.get(f"i{i}", b.get(f"inning{i}", "")))
        inning_results[i] = str(v).strip() if v else ""

    return {
        "order":    str(b.get("batOrder", b.get("order", ""))),
        "pos":      str(b.get("position", b.get("pos", ""))),
        "name":     str(b.get("playerName", b.get("name", ""))),
        "innings":  inning_results,   # {1: "좌안", 2: "", ...}
        "ab":       str(b.get("ab", b.get("atBat", "0"))),
        "h":        str(b.get("hit", b.get("h", "0"))),
        "rbi":      str(b.get("rbi", "0")),
        "r":        str(b.get("run", b.get("r", "0"))),
        "avg":      str(b.get("avg", b.get("average", "0.000"))),
    }


def _parse_pitcher_data(data: dict, game: dict):
    """투수 기록 파싱."""
    away_list = _find_list(data, ["away", "awayPitchers", "visitorPitchers"])
    home_list = _find_list(data, ["home", "homePitchers"])

    if away_list and not game["away_pitchers"]:
        game["away_pitchers"] = [_parse_pitcher_row(p) for p in away_list]
    if home_list and not game["home_pitchers"]:
        game["home_pitchers"] = [_parse_pitcher_row(p) for p in home_list]


def _parse_pitcher_row(p: dict) -> dict:
    return {
        "name":    str(p.get("playerName", p.get("name", ""))),
        "debut":   str(p.get("debut", p.get("debutInning", "선발"))),
        "result":  str(p.get("result", "")),
        "win":     str(p.get("win", p.get("w", "0"))),
        "lose":    str(p.get("lose", p.get("l", "0"))),
        "save":    str(p.get("save", p.get("sv", "0"))),
        "ip":      str(p.get("ip", p.get("inningPitched", "0"))),
        "bf":      str(p.get("bf", p.get("batterFaced", "0"))),
        "np":      str(p.get("np", p.get("pitchCount", "0"))),
        "ab":      str(p.get("ab", "0")),
        "h":       str(p.get("hit", p.get("h", "0"))),
        "hr":      str(p.get("hr", p.get("homeRun", "0"))),
        "bb":      str(p.get("bb", p.get("walk", "0"))),
        "so":      str(p.get("so", p.get("strikeOut", "0"))),
        "r":       str(p.get("run", p.get("r", "0"))),
        "er":      str(p.get("er", p.get("earnedRun", "0"))),
        "era":     str(p.get("era", "0.00")),
    }


def _parse_key_records(data: dict, game: dict):
    """주요 기록(홈런, 결승타 등) 파싱."""
    if game["key_records"]:
        return

    flat = _flatten(data)
    records = []
    for key, val in flat.items():
        if val and isinstance(val, str) and len(val) > 2:
            kl = key.lower()
            if any(k in kl for k in ["homerun", "hr", "홈런"]):
                records.append(f"홈런: {val}")
            elif any(k in kl for k in ["winning", "결승"]):
                records.append(f"결승타: {val}")
            elif any(k in kl for k in ["double", "2루타"]):
                records.append(f"2루타: {val}")
            elif any(k in kl for k in ["triple", "3루타"]):
                records.append(f"3루타: {val}")
            elif any(k in kl for k in ["steal", "도루"]):
                records.append(f"도루: {val}")

    game["key_records"] = records


# ── 유틸 ──
def _find_list(data: dict, keys: list) -> list | None:
    for key in keys:
        val = data.get(key)
        if isinstance(val, list) and val:
            return val
    # 재귀 탐색
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, dict):
                result = _find_list(v, keys)
                if result:
                    return result
    return None


def _flatten(data, prefix="", result=None):
    if result is None:
        result = {}
    if isinstance(data, dict):
        for k, v in data.items():
            _flatten(v, f"{prefix}{k}.", result)
    elif isinstance(data, list):
        for i, v in enumerate(data[:3]):  # 처음 3개만
            _flatten(v, f"{prefix}{i}.", result)
    else:
        result[prefix.rstrip(".")] = data
    return result


# ──────────────────────────────────────────────
# 3. 마크다운 생성
# ──────────────────────────────────────────────

def format_markdown(game: dict) -> str:
    """game dict를 기존 raw 파일 형식의 마크다운으로 변환."""
    away_kr = game["away_kr"]
    home_kr = game["home_kr"]
    away_score = game["away_score"]
    home_score = game["home_score"]

    date_str = game["date_str"]  # "20260408"
    y, m, d = date_str[:4], date_str[4:6], date_str[6:]
    date_display = f"{y}년 {int(m)}월 {int(d)}일"

    lines = [
        f"# {away_kr} {away_score} vs {home_score} {home_kr}",
        "",
        f"- **날짜**: {date_display}",
        f"- **경기 ID**: {game['game_id']}",
        f"- **구장**: {game['stadium']}",
        f"- **관중**: {game['attendance']}",
        f"- **개시**: {game['start_time']}",
        f"- **종료**: {game['end_time']}",
        f"- **경기시간**: {game['duration']}",
        "",
    ]

    # 스코어보드
    lines.append("## 스코어보드")
    lines.append("| 팀 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | R | H | E | B |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    if game["scoreboard"]:
        for row in game["scoreboard"]:
            # row: [팀, i1..i12, R, H, E, B] (최대 17개)
            padded = list(row) + ["-"] * 17
            team  = padded[0]
            inn   = padded[1:13]
            rheb  = padded[13:17]
            lines.append("| " + " | ".join([str(team)] + [str(v) for v in inn] + [str(v) for v in rheb]) + " |")
    else:
        # 스코어보드를 파싱 못한 경우 최소한 결과만
        lines.append(f"| {away_kr} | - | - | - | - | - | - | - | - | - | - | - | - | {away_score} | - | - | - |")
        lines.append(f"| {home_kr} | - | - | - | - | - | - | - | - | - | - | - | - | {home_score} | - | - | - |")
    lines.append("")

    # 주요 기록
    lines.append("## 주요 기록")
    if game["key_records"]:
        for rec in game["key_records"]:
            lines.append(f"- **{rec.split(':')[0]}**: {rec.split(':', 1)[-1].strip()}" if ":" in rec else f"- {rec}")
    else:
        lines.append("- (데이터 없음)")
    lines.append("")

    # 타자 기록
    for team_kr, batters in [(away_kr, game["away_batters"]), (home_kr, game["home_batters"])]:
        lines.append(f"## {team_kr} 타자 기록")
        lines.append("| 타순 | 포지션 | 선수명 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 타수 | 안타 | 타점 | 득점 | 타율 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for b in batters:
            inn_vals = [b["innings"].get(i, "") for i in range(1, 10)]
            lines.append(
                f"| {b['order']} | {b['pos']} | {b['name']} | "
                + " | ".join(inn_vals)
                + f" | {b['ab']} | {b['h']} | {b['rbi']} | {b['r']} | {b['avg']} |"
            )
        lines.append("")

    # 투수 기록
    for team_kr, pitchers in [(away_kr, game["away_pitchers"]), (home_kr, game["home_pitchers"])]:
        lines.append(f"## {team_kr} 투수 기록")
        lines.append("| 선수명 | 등판 | 결과 | 승 | 패 | 세 | 이닝 | 타자 | 투구수 | 타수 | 피안타 | 홈런 | 4사구 | 삼진 | 실점 | 자책 | 평균자책점 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for p in pitchers:
            lines.append(
                f"| {p['name']} | {p['debut']} | {p['result']} | "
                f"{p['win']} | {p['lose']} | {p['save']} | {p['ip']} | "
                f"{p['bf']} | {p['np']} | {p['ab']} | {p['h']} | "
                f"{p['hr']} | {p['bb']} | {p['so']} | {p['r']} | {p['er']} | {p['era']} |"
            )
        lines.append("")

    # 경기 결과
    lines.append("## 경기 결과")
    lines.append(f"- **승리 투수**: {game['winner']}")
    lines.append(f"- **패전 투수**: {game['loser']}")
    if game["save"]:
        lines.append(f"- **세이브**: {game['save']}")
    lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 4. 파일 저장
# ──────────────────────────────────────────────

def save_game(game: dict, content: str):
    """raw/articles/kbo/2026/YYYYMMDD/ 에 마크다운 저장."""
    date_str = game["date_str"]
    out_dir  = os.path.join(RAW_DIR, date_str)
    os.makedirs(out_dir, exist_ok=True)

    away_en = game["away_en"]
    home_en = game["home_en"]
    away_kr = game["away_kr"]
    home_kr = game["home_kr"]
    game_id = game["game_id"]

    filename = f"{game_id}_{away_kr}_vs_{home_kr}.md"
    filepath = os.path.join(out_dir, filename)

    if os.path.exists(filepath):
        print(f"  [SKIP] 이미 존재: {filename}")
        return False

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [SAVE] {filename}")
    return True


# ──────────────────────────────────────────────
# 5. 메인
# ──────────────────────────────────────────────

async def main():
    # 날짜 결정: 인수 우선, 없으면 전날 KST
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and re.match(r"\d{8}", args[0]):
        date_str = args[0]
    else:
        date_str = (datetime.now(KST) - timedelta(days=1)).strftime("%Y%m%d")

    print(f"[KBO Scraper] 수집 대상: {date_str}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            locale="ko-KR",
        )

        # 1) 경기 ID 목록 수집
        page = await context.new_page()
        game_ids = await get_game_ids(page, date_str)
        await page.close()

        if not game_ids:
            print(f"[KBO Scraper] {date_str} 경기 없음 (우천취소 또는 비경기일)")
            await browser.close()
            return

        print(f"[KBO Scraper] 경기 {len(game_ids)}개 발견: {game_ids}")

        # 2) 경기별 데이터 수집 & 저장
        saved = 0
        for game_id in game_ids:
            print(f"  → {game_id} 수집 중...")
            try:
                page = await context.new_page()
                game = await get_game_data(page, game_id)
                await page.close()

                if not game:
                    print(f"  [WARN] {game_id}: 데이터 파싱 실패 (경기 미완료 또는 구조 변경)")
                    continue

                content = format_markdown(game)
                if save_game(game, content):
                    saved += 1

            except Exception as e:
                print(f"  [ERROR] {game_id}: {e}")

        await browser.close()

    print(f"\n[KBO Scraper] 완료: {saved}/{len(game_ids)} 저장")

    if saved > 0:
        print("[KBO Scraper] rebuild_kbo_wiki.py 실행 중...")
        os.system(f"python3 {os.path.join(BASE_DIR, 'scripts', 'rebuild_kbo_wiki.py')}")


if __name__ == "__main__":
    asyncio.run(main())
