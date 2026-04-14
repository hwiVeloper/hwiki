#!/usr/bin/env python3
"""raw/articles/kbo/ 데이터를 기반으로 wiki/baseball/kbo/ 전체 재구성"""

import os
import re
import sys
import glob
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# Windows 콘솔에서 이모지 print가 cp949로 인코딩 실패하는 것 방지
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KST = timezone(timedelta(hours=9))
LOG_MARKER_RE = re.compile(r"<!--\s*last-kbo-ingest-date:\s*(\d{4}-\d{2}-\d{2})\s*-->")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "raw/articles/kbo/2026")
WIKI_DIR = os.path.join(BASE, "wiki/baseball/kbo")

TEAM_CODE = {
    "두산": "doosan", "NC": "nc", "삼성": "samsung", "한화": "hanwha",
    "KT": "kt", "LG": "lg", "KIA": "kia", "SSG": "ssg",
    "롯데": "lotte", "키움": "kiwoom",
}
TEAM_FULL = {
    "두산": "두산 베어스", "NC": "NC 다이노스", "삼성": "삼성 라이온즈",
    "한화": "한화 이글스", "KT": "KT 위즈", "LG": "LG 트윈스",
    "KIA": "KIA 타이거즈", "SSG": "SSG 랜더스", "롯데": "롯데 자이언츠",
    "키움": "키움 히어로즈",
}
TEAM_STADIUM = {
    "두산": "잠실", "LG": "잠실", "NC": "창원NC파크", "삼성": "대구",
    "한화": "한화생명이글스파크(대전)", "KT": "수원KT위즈파크",
    "KIA": "광주기아챔피언스필드", "SSG": "인천SSG랜더스필드",
    "롯데": "사직", "키움": "고척스카이돔",
}

# ── Parse one game file ──
def parse_game(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    game = {"filepath": filepath, "batters": {}, "pitchers": {}}

    # Title: "# KT 11 vs 7 LG" or "# 키움 5 vs 2 두산"
    title_m = re.match(r"^#\s+(.+?)\s+(\d+)\s+vs\s+(\d+)\s+(.+)", lines[0])
    if not title_m:
        return None
    game["away_name"] = title_m.group(1).strip()
    game["away_score"] = int(title_m.group(2))
    game["home_score"] = int(title_m.group(3))
    game["home_name"] = title_m.group(4).strip()

    # Meta fields
    for line in lines[1:30]:
        if "**날짜**" in line:
            m = re.search(r"(\d+)년\s*(\d+)월\s*(\d+)일", line)
            if m:
                game["date"] = f"{m.group(1)}.{int(m.group(2)):02d}.{int(m.group(3)):02d}"
                game["date_short"] = f"{int(m.group(2)):02d}.{int(m.group(3)):02d}"
        elif "**구장**" in line:
            game["stadium"] = line.split(":")[-1].strip()
        elif "**관중**" in line:
            game["attendance"] = line.split(":")[-1].strip().replace(",", "")
        elif "**경기시간**" in line:
            game["duration"] = line.split(":")[-1].strip()
        elif "**경기 ID**" in line:
            game["game_id"] = line.split(":")[-1].strip()

    # Key records section
    key_records = []
    in_key = False
    for line in lines:
        if line.strip() == "## 주요 기록":
            in_key = True
            continue
        if in_key:
            if line.startswith("## "):
                break
            if line.strip().startswith("- "):
                key_records.append(line.strip()[2:])
    game["key_records"] = key_records

    # Winner/loser
    game["winner"] = ""
    game["loser"] = ""
    game["save"] = ""
    for line in lines:
        if "**승리 투수**" in line:
            game["winner"] = line.split(":")[-1].strip()
        elif "**패전 투수**" in line:
            game["loser"] = line.split(":")[-1].strip()
        elif "**세이브**" in line:
            game["save"] = line.split(":")[-1].strip()

    # Determine result
    if game["away_score"] > game["home_score"]:
        game["away_result"] = "승"
        game["home_result"] = "패"
    elif game["away_score"] < game["home_score"]:
        game["away_result"] = "패"
        game["home_result"] = "승"
    else:
        game["away_result"] = "무"
        game["home_result"] = "무"

    # Parse batter tables
    current_team = None
    in_table = False
    header_found = False
    for line in lines:
        if "타자 기록" in line and line.startswith("##"):
            team_m = re.match(r"##\s+(.+?)\s+타자", line)
            if team_m:
                current_team = team_m.group(1).strip()
                in_table = False
                header_found = False
            continue
        if current_team and "| 타순 |" in line:
            header_found = True
            continue
        if current_team and header_found and "| --- |" in line:
            in_table = True
            continue
        if current_team and in_table:
            if not line.strip().startswith("|"):
                current_team = None
                in_table = False
                header_found = False
                continue
            # Keep all columns including empty ones (innings may be blank)
            raw_cols = line.split("|")
            cols = [c.strip() for c in raw_cols]
            # Skip TOTAL rows
            if any(x in line for x in ["TOTAL", "****"]):
                continue
            if len(cols) < 10:
                continue
            try:
                # Use positive index for first cols, negative for stats
                # Format: |타순|포지션|선수명|1|2|...|9|...|타수|안타|타점|득점|타율|
                name = cols[3]  # after leading empty from split
                pos = cols[2]
                if not name or name in ("****", "TOTAL", "**TOTAL**"):
                    continue
                avg_str = cols[-2]  # last non-empty before trailing ""
                r = int(cols[-3]) if cols[-3].lstrip("-").isdigit() else 0
                rbi = int(cols[-4]) if cols[-4].lstrip("-").isdigit() else 0
                h = int(cols[-5]) if cols[-5].lstrip("-").isdigit() else 0
                ab = int(cols[-6]) if cols[-6].lstrip("-").isdigit() else 0

                if current_team not in game["batters"]:
                    game["batters"][current_team] = {}
                if name not in game["batters"][current_team]:
                    game["batters"][current_team][name] = {
                        "pos": pos, "ab": ab, "h": h, "rbi": rbi, "r": r, "avg": avg_str
                    }
                else:
                    existing = game["batters"][current_team][name]
                    existing["ab"] += ab
                    existing["h"] += h
                    existing["rbi"] += rbi
                    existing["r"] += r
            except (ValueError, IndexError):
                pass

    # Parse pitcher tables
    current_team = None
    in_table = False
    header_found = False
    for line in lines:
        if "투수 기록" in line and line.startswith("##"):
            team_m = re.match(r"##\s+(.+?)\s+투수", line)
            if team_m:
                current_team = team_m.group(1).strip()
                in_table = False
                header_found = False
            continue
        if current_team and "| 선수명 |" in line:
            header_found = True
            continue
        if current_team and header_found and "| --- |" in line:
            in_table = True
            continue
        if current_team and in_table:
            if not line.strip().startswith("|"):
                current_team = None
                in_table = False
                header_found = False
                continue
            # 경계 | 만 제거하고 내부 빈 칸은 보존 (결과 칸이 비어도 인덱스 일관성 유지)
            cols = [c.strip() for c in line.split("|")]
            if cols and cols[0] == "":
                cols = cols[1:]
            if cols and cols[-1] == "":
                cols = cols[:-1]
            if not cols or cols[0] in ("****", "TOTAL", "**TOTAL**"):
                continue
            if len(cols) >= 10:
                try:
                    name = cols[0]
                    if not name or name in ("****", "TOTAL", "**TOTAL**"):
                        continue
                    # 헤더: 선수명(0)|등판(1)|결과(2)|승(3)|패(4)|세(5)|이닝(6)|타자(7)|투구수(8)|타수(9)|피안타(10)|홈런(11)|4사구(12)|삼진(13)|실점(14)|자책(15)|ERA(16)
                    result = cols[2]
                    ip_str = cols[6]
                    ha = cols[10] if len(cols) > 10 else "0"
                    k = cols[13] if len(cols) > 13 else "0"
                    runs = cols[14] if len(cols) > 14 else "0"
                    er = cols[15] if len(cols) > 15 else "0"
                    era = cols[16] if len(cols) > 16 else ""
                    pitches = cols[8] if len(cols) > 8 else "0"

                    if current_team not in game.get("pitchers", {}):
                        game["pitchers"][current_team] = {}
                    game["pitchers"][current_team][name] = {
                        "result": result,
                        "ip": ip_str,
                        "ha": ha,
                        "k": k,
                        "runs": runs,
                        "er": er,
                        "era": era,
                        "pitches": pitches,
                    }
                except (ValueError, IndexError):
                    pass

    return game


# ── Generate source page ──
def gen_source(game):
    away = game["away_name"]
    home = game["home_name"]
    ac = TEAM_CODE.get(away, away.lower())
    hc = TEAM_CODE.get(home, home.lower())
    date_raw = game.get("date", "").replace(".", "")

    # Key records - pick top 3-5
    key_lines = []
    for kr in game.get("key_records", [])[:5]:
        key_lines.append(f"- {kr}")
    key_section = "\n".join(key_lines) if key_lines else "- 특이 기록 없음"

    # Top performers from batters
    performers = []
    for team_name, batters in game.get("batters", {}).items():
        tc = TEAM_CODE.get(team_name, team_name.lower())
        for name, stats in batters.items():
            if stats["h"] >= 2 or stats["rbi"] >= 2 or stats["r"] >= 2:
                performers.append(f"- {name} ({team_name}): {stats['ab']}타수 {stats['h']}안타 {stats['rbi']}타점 {stats['r']}득점")
    performer_section = "\n".join(performers[:5]) if performers else "- 특기할 활약 없음"

    result_text = f"{away} {game['away_score']} - {game['home_score']} {home}"

    content = f"""---
type: source
source: {os.path.relpath(game['filepath'], BASE)}
---

# {away} vs {home} {game.get('date', '')} 경기 요약

## 개요
- **결과**: {result_text}
- **구장**: {game.get('stadium', '')} | **관중**: {game.get('attendance', '')}
- **경기시간**: {game.get('duration', '')}

## 핵심 내용
{key_section}

## 주요 선수
{performer_section}

## 경기 결과
- **승리 투수**: {game.get('winner', '')}
- **패전 투수**: {game.get('loser', '')}
{f"- **세이브**: {game['save']}" if game.get('save') else ""}

## 관련 항목
- [[{ac}]] | [[{hc}]]
- [[kbo-2026-season]]
"""
    return content.strip() + "\n"


# ── log.md 갱신 ──
def update_log(games):
    """log.md에 KBO 자동 수집 엔트리를 멱등적으로 추가한다.

    파일 끝의 `<!-- last-kbo-ingest-date: YYYY-MM-DD -->` 워터마크를 기준으로
    - 마커가 없으면: 기존 로그를 건드리지 않고 현재 최신 경기 날짜로 마커만 설치.
    - 마커보다 늦은 raw 데이터가 있으면: 해당 구간만 요약한 엔트리를 append.
    """
    log_path = os.path.join(BASE, "wiki/log.md")
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            existing = f.read()
    except FileNotFoundError:
        return False

    raw_dates = sorted({g.get("date", "").replace(".", "-") for g in games if g.get("date")})
    if not raw_dates:
        return False
    latest_raw = raw_dates[-1]

    m = LOG_MARKER_RE.search(existing)
    if not m:
        # 첫 실행: 백필 엔트리 없이 워터마크만 설치
        new_content = existing.rstrip() + f"\n\n<!-- last-kbo-ingest-date: {latest_raw} -->\n"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"📝 log.md 워터마크 초기화: {latest_raw}")
        return True

    last_logged = m.group(1)
    new_dates = [d for d in raw_dates if d > last_logged]
    if not new_dates:
        return False

    new_set = set(new_dates)
    new_game_count = sum(1 for g in games if g.get("date", "").replace(".", "-") in new_set)

    today_kst = datetime.now(KST).strftime("%Y-%m-%d")
    range_str = new_dates[0] if len(new_dates) == 1 else f"{new_dates[0]} ~ {new_dates[-1]}"

    entry = (
        f"\n## [{today_kst}] ingest | KBO 자동 수집 ({range_str})\n"
        f"- 신규 경기 {new_game_count}개 반영 ({len(new_dates)}일치)\n"
        f"- games / teams / players / kbo-2026-season / index 재생성\n"
    )

    without_marker = LOG_MARKER_RE.sub("", existing).rstrip()
    new_content = without_marker + "\n" + entry + f"\n<!-- last-kbo-ingest-date: {latest_raw} -->\n"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"📝 log.md 추가: {range_str} ({new_game_count}경기)")
    return True


# ── Main ──
def main():
    # Find all individual game files (exclude all_games)
    game_files = sorted(glob.glob(os.path.join(RAW_DIR, "*/*_vs_*.md")))
    print(f"📂 {len(game_files)}개 경기 파일 발견")

    games = []
    team_games = defaultdict(list)  # team_name -> [game]
    player_stats = defaultdict(lambda: {"team": "", "games": [], "totals": {"ab": 0, "h": 0, "rbi": 0, "r": 0}})
    pitcher_stats = defaultdict(lambda: {"team": "", "games": []})

    for gf in game_files:
        game = parse_game(gf)
        if not game:
            print(f"  ⚠️ 파싱 실패: {gf}")
            continue
        games.append(game)
        team_games[game["away_name"]].append(game)
        team_games[game["home_name"]].append(game)

        # Aggregate batter stats
        for team_name, batters in game.get("batters", {}).items():
            for name, stats in batters.items():
                key = f"{team_name}_{name}"
                player_stats[key]["team"] = team_name
                player_stats[key]["name"] = name
                player_stats[key]["games"].append({
                    "date": game.get("date_short", ""),
                    "opponent": game["home_name"] if team_name == game["away_name"] else game["away_name"],
                    "ab": stats["ab"], "h": stats["h"], "rbi": stats["rbi"], "r": stats["r"],
                })
                player_stats[key]["totals"]["ab"] += stats["ab"]
                player_stats[key]["totals"]["h"] += stats["h"]
                player_stats[key]["totals"]["rbi"] += stats["rbi"]
                player_stats[key]["totals"]["r"] += stats["r"]

        # Aggregate pitcher stats
        for team_name, pitchers in game.get("pitchers", {}).items():
            for name, stats in pitchers.items():
                key = f"{team_name}_{name}"
                pitcher_stats[key]["team"] = team_name
                pitcher_stats[key]["name"] = name
                pitcher_stats[key]["games"].append({
                    "date": game.get("date_short", ""),
                    "opponent": game["home_name"] if team_name == game["away_name"] else game["away_name"],
                    "result": stats.get("result", ""),
                    "ip": stats.get("ip", ""),
                    "ha": stats.get("ha", ""),
                    "k": stats.get("k", ""),
                    "runs": stats.get("runs", ""),
                    "er": stats.get("er", ""),
                    "era": stats.get("era", ""),
                    "pitches": stats.get("pitches", ""),
                })

    print(f"✅ {len(games)}개 경기 파싱 완료")
    print(f"📊 타자 {len(player_stats)}명, 투수 {len(pitcher_stats)}명 집계")

    # ── Write source pages ──
    os.makedirs(os.path.join(WIKI_DIR, "games"), exist_ok=True)
    source_count = 0
    for game in games:
        away = game["away_name"]
        home = game["home_name"]
        ac = TEAM_CODE.get(away, away.lower())
        hc = TEAM_CODE.get(home, home.lower())
        date_raw = game.get("date", "").replace(".", "")
        fname = f"source-{ac}-vs-{hc}-{date_raw}.md"
        fpath = os.path.join(WIKI_DIR, "games", fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(gen_source(game))
        source_count += 1
    print(f"📝 source 페이지 {source_count}개 생성")

    # ── Write team pages ──
    os.makedirs(os.path.join(WIKI_DIR, "teams"), exist_ok=True)
    for team_name, tgames in team_games.items():
        tc = TEAM_CODE.get(team_name, team_name.lower())
        full = TEAM_FULL.get(team_name, team_name)

        wins = sum(1 for g in tgames if (g["away_name"] == team_name and g["away_result"] == "승") or (g["home_name"] == team_name and g["home_result"] == "승"))
        losses = sum(1 for g in tgames if (g["away_name"] == team_name and g["away_result"] == "패") or (g["home_name"] == team_name and g["home_result"] == "패"))
        draws = sum(1 for g in tgames if (g["away_name"] == team_name and g["away_result"] == "무") or (g["home_name"] == team_name and g["home_result"] == "무"))

        game_rows = []
        for g in sorted(tgames, key=lambda x: x.get("date", "")):
            if g["away_name"] == team_name:
                opp = g["home_name"]
                opp_c = TEAM_CODE.get(opp, opp.lower())
                score = f"{g['away_score']}-{g['home_score']}"
                result = g["away_result"]
                loc = "원정"
            else:
                opp = g["away_name"]
                opp_c = TEAM_CODE.get(opp, opp.lower())
                score = f"{g['home_score']}-{g['away_score']}"
                result = g["home_result"]
                loc = "홈"
            game_rows.append(f"| {g.get('date_short','')} | [[{opp_c}\\|{opp}]] | {loc} | {result} | {score} |")

        game_table = "\n".join(game_rows)

        # Key players for this team
        team_batters = [(k, v) for k, v in player_stats.items() if v["team"] == team_name]
        team_batters.sort(key=lambda x: x[1]["totals"]["h"], reverse=True)

        player_lines = []
        for key, ps in team_batters[:15]:
            t = ps["totals"]
            avg = f".{int(t['h']/t['ab']*1000):03d}" if t["ab"] > 0 else ".000"
            name_slug = to_slug(ps["name"])
            player_lines.append(f"- [[{name_slug}\\|{ps['name']}]] — {len(ps['games'])}경기 {t['ab']}타수 {t['h']}안타 {t['rbi']}타점 {avg}")

        team_pitchers_list = [(k, v) for k, v in pitcher_stats.items() if v["team"] == team_name]
        for key, ps in team_pitchers_list[:10]:
            name_slug = to_slug(ps["name"])
            player_lines.append(f"- [[{name_slug}\\|{ps['name']}]] (투수) — {len(ps['games'])}경기")

        player_section = "\n".join(player_lines) if player_lines else ""

        content = f"""---
type: entity
---

# {full}

KBO 리그 소속 프로야구단.

## 2026 시즌 초반 성적

**{len(tgames)}경기: {wins}승 {losses}패 {draws}무**

| 날짜 | 상대 | 홈/원정 | 결과 | 스코어 |
|------|------|---------|------|--------|
{game_table}

## 주요 선수
{player_section}

## 관련 항목
- [[kbo-2026-season]]
"""
        fpath = os.path.join(WIKI_DIR, "teams", f"{tc}.md")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")

    print(f"📝 팀 페이지 {len(team_games)}개 생성")

    # ── Write player pages ──
    os.makedirs(os.path.join(WIKI_DIR, "players"), exist_ok=True)
    player_count = 0

    # Batters
    for key, ps in player_stats.items():
        if len(ps["games"]) < 2 and ps["totals"]["ab"] < 3:
            continue  # Skip players with minimal appearances

        name = ps["name"]
        team = ps["team"]
        tc = TEAM_CODE.get(team, team.lower())
        t = ps["totals"]
        avg = f".{int(t['h']/t['ab']*1000):03d}" if t["ab"] > 0 else ".000"

        game_rows = []
        for g in ps["games"]:
            opp_c = TEAM_CODE.get(g["opponent"], g["opponent"].lower())
            game_rows.append(f"| {g['date']} | [[{opp_c}\\|{g['opponent']}]] | {g['ab']} | {g['h']} | {g['rbi']} | {g['r']} |")

        game_table = "\n".join(game_rows)

        name_slug = to_slug(name)
        content = f"""---
type: entity
---

# {name}

[[{tc}]] 소속.

## 2026 시즌 초반 타격 성적

| 날짜 | 상대 | 타수 | 안타 | 타점 | 득점 |
|------|------|------|------|------|------|
{game_table}

**통산**: {len(ps['games'])}경기 {t['ab']}타수 {t['h']}안타 {t['rbi']}타점 {t['r']}득점 타율 **{avg}**

## 관련 항목
- [[{tc}]] | [[kbo-2026-season]]
"""
        fpath = os.path.join(WIKI_DIR, "players", f"{name_slug}.md")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        player_count += 1

    # Pitchers (only if not already created as batter)
    for key, ps in pitcher_stats.items():
        name = ps["name"]
        team = ps["team"]
        tc = TEAM_CODE.get(team, team.lower())
        name_slug = to_slug(name)
        fpath = os.path.join(WIKI_DIR, "players", f"{name_slug}.md")

        if os.path.exists(fpath):
            # Append pitching stats to existing page
            with open(fpath, "r", encoding="utf-8") as f:
                existing = f.read()
            if "투수 성적" not in existing:
                game_rows = []
                for g in ps["games"]:
                    opp_c = TEAM_CODE.get(g["opponent"], g["opponent"].lower())
                    game_rows.append(f"| {g['date']} | [[{opp_c}\\|{g['opponent']}]] | {g.get('ip','')} | {g.get('pitches','')} | {g.get('ha','')} | {g.get('k','')} | {g.get('runs','')} | {g.get('er','')} |")
                game_table = "\n".join(game_rows)

                pitch_section = f"""

## 2026 시즌 초반 투수 성적

| 날짜 | 상대 | 이닝 | 투구수 | 피안타 | 삼진 | 실점 | 자책 |
|------|------|------|--------|--------|------|------|------|
{game_table}
"""
                # Insert before 관련 항목
                existing = existing.replace("## 관련 항목", pitch_section.strip() + "\n\n## 관련 항목")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(existing)
            continue

        if len(ps["games"]) < 1:
            continue

        game_rows = []
        for g in ps["games"]:
            opp_c = TEAM_CODE.get(g["opponent"], g["opponent"].lower())
            game_rows.append(f"| {g['date']} | [[{opp_c}\\|{g['opponent']}]] | {g.get('result','')} | {g.get('ip','')} | {g.get('pitches','')} | {g.get('ha','')} | {g.get('k','')} | {g.get('runs','')} | {g.get('er','')} |")

        game_table = "\n".join(game_rows)

        content = f"""---
type: entity
---

# {name}

[[{tc}]] 소속 투수.

## 2026 시즌 초반 투수 성적

| 날짜 | 상대 | 결과 | 이닝 | 투구수 | 피안타 | 삼진 | 실점 | 자책 |
|------|------|------|------|--------|--------|------|------|------|
{game_table}

## 관련 항목
- [[{tc}]] | [[kbo-2026-season]]
"""
        fpath_out = os.path.join(WIKI_DIR, "players", f"{name_slug}.md")
        with open(fpath_out, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        player_count += 1

    print(f"📝 선수 페이지 {player_count}개 생성")

    # ── Update kbo-2026-season.md ──
    all_game_rows = []
    for g in sorted(games, key=lambda x: x.get("date", "")):
        ac = TEAM_CODE.get(g["away_name"], g["away_name"].lower())
        hc = TEAM_CODE.get(g["home_name"], g["home_name"].lower())
        date_raw = g.get("date", "").replace(".", "")
        src = f"source-{ac}-vs-{hc}-{date_raw}"
        all_game_rows.append(f"| {g.get('date_short','')} | {g['away_name']} vs {g['home_name']} | {g['away_score']}-{g['home_score']} | [[{src}]] |")

    game_list = "\n".join(all_game_rows)

    # Team standings
    standings = []
    for team_name in TEAM_CODE:
        tg = team_games.get(team_name, [])
        if not tg:
            continue
        w = sum(1 for g in tg if (g["away_name"] == team_name and g["away_result"] == "승") or (g["home_name"] == team_name and g["home_result"] == "승"))
        l = sum(1 for g in tg if (g["away_name"] == team_name and g["away_result"] == "패") or (g["home_name"] == team_name and g["home_result"] == "패"))
        d = sum(1 for g in tg if (g["away_name"] == team_name and g["away_result"] == "무") or (g["home_name"] == team_name and g["home_result"] == "무"))
        tc = TEAM_CODE[team_name]
        pct = w / (w + l) if (w + l) > 0 else 0
        standings.append((pct, w, l, d, team_name, tc))
    standings.sort(key=lambda x: (-x[0], -x[1]))

    standing_rows = []
    for i, (pct, w, l, d, tn, tc) in enumerate(standings, 1):
        standing_rows.append(f"| {i} | [[{tc}\\|{tn}]] | {w} | {l} | {d} | .{int(pct*1000):03d} |")
    standing_table = "\n".join(standing_rows)

    # 최신 경기 날짜 (순위 헤더 라벨용)
    latest_date = max((g.get("date", "") for g in games if g.get("date")), default="")
    if latest_date:
        y, m, d = latest_date.split(".")
        standings_label = f"{int(m)}월 {int(d)}일 기준"
    else:
        standings_label = "기준일 없음"

    season_content = f"""---
type: concept
---

# KBO 2026 시즌

2026년 KBO 리그 정규시즌. 2026년 3월 28일 개막.

## 순위 ({standings_label})

| 순위 | 팀 | 승 | 패 | 무 | 승률 |
|------|------|----|----|----|----|
{standing_table}

## 전체 경기 기록

| 날짜 | 경기 | 스코어 | 출처 |
|------|------|--------|------|
{game_list}

## 관련 항목
{chr(10).join(f'- [[{tc}]]' for tc in TEAM_CODE.values())}
"""
    fpath = os.path.join(WIKI_DIR, "kbo-2026-season.md")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(season_content.strip() + "\n")
    print("📝 kbo-2026-season.md 업데이트")

    # ── Update index.md ──
    # Generate team index
    team_index = []
    for tn in sorted(TEAM_CODE.keys()):
        tc = TEAM_CODE[tn]
        full = TEAM_FULL.get(tn, tn)
        team_index.append(f"- [[{tc}]] — {full}")

    # Generate player index by team
    player_index_parts = []
    for tn in sorted(TEAM_CODE.keys()):
        tc = TEAM_CODE[tn]
        team_players = []
        # Batters
        for key, ps in sorted(player_stats.items(), key=lambda x: -x[1]["totals"]["h"]):
            if ps["team"] == tn and (len(ps["games"]) >= 2 or ps["totals"]["ab"] >= 3):
                slug = to_slug(ps["name"])
                team_players.append(f"- [[{slug}]] — {ps['name']}")
        # Pitchers not in batters
        for key, ps in pitcher_stats.items():
            if ps["team"] == tn:
                slug = to_slug(ps["name"])
                batter_key = f"{tn}_{ps['name']}"
                if batter_key not in player_stats or len(player_stats[batter_key]["games"]) < 2:
                    if len(ps["games"]) >= 1:
                        entry = f"- [[{slug}]] — {ps['name']} (투수)"
                        if entry not in team_players:
                            team_players.append(entry)

        if team_players:
            player_index_parts.append(f"#### {tn}")
            player_index_parts.extend(team_players)
            player_index_parts.append("")

    # Generate source index
    source_index = []
    for g in sorted(games, key=lambda x: x.get("date", "")):
        ac = TEAM_CODE.get(g["away_name"], g["away_name"].lower())
        hc = TEAM_CODE.get(g["home_name"], g["home_name"].lower())
        date_raw = g.get("date", "").replace(".", "")
        src = f"source-{ac}-vs-{hc}-{date_raw}"
        source_index.append(f"- [[{src}]] — {g['away_name']} vs {g['home_name']} {g.get('date','')}")

    index_content = f"""# hwiki Index

## 야구

> `wiki/baseball/kbo/`

### 팀 (`teams/`)
{chr(10).join(team_index)}

### 선수 (`players/`)

{chr(10).join(player_index_parts)}

### 개념
- [[kbo-2026-season]] — 2026 KBO 시즌

### 경기 기록 (`games/`)
{chr(10).join(source_index)}

## 음악

## 영상

## 개발

> `wiki/dev/`

### 개념
- [[llm-wiki]] — LLM Wiki (Karpathy의 LLM 기반 지식 베이스 패턴)

### 자료
- [[source-llm-wiki-seminar]] — LLM Wiki 패턴 완벽 해부 세미나

## 기타
"""
    fpath = os.path.join(BASE, "wiki/index.md")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(index_content.strip() + "\n")
    print("📝 index.md 업데이트")

    # ── log.md 갱신 ──
    update_log(games)

    print(f"\n🏁 완료! source {source_count} + 팀 {len(team_games)} + 선수 {player_count} + concept 1 + index 1")


def to_slug(name):
    """Korean name to kebab-case slug using romanization mapping"""
    KNOWN = {
        # 두산
        "양의지": "yang-eui-ji", "카메론": "cameron", "박준순": "park-jun-sun",
        "안재석": "ahn-jae-seok", "박찬호": "park-chan-ho", "정수빈": "jung-su-bin",
        "양석환": "yang-seok-hwan", "강승호": "kang-seung-ho", "김민석": "kim-min-seok",
        "박지훈": "park-ji-hun", "잭로그": "zach-logue", "플렉센": "flexen",
        "타무라": "tamura", "김택연": "kim-taek-yeon", "곽빈": "gwak-bin",
        "최민석": "choi-min-seok", "최승용": "choi-seung-yong", "이병헌": "lee-byung-hun",
        "양재훈": "yang-jae-hun", "박신지": "park-shin-ji", "이용찬": "lee-yong-chan",
        "최지강": "choi-ji-gang", "박치국": "park-chi-guk", "최원준": "choi-won-jun",
        "김정우": "kim-jung-woo", "윤태호": "yoon-tae-ho", "박정수": "park-jung-soo",
        "김인태": "kim-in-tae", "윤준호": "yoon-jun-ho", "이유찬": "lee-yu-chan",
        "오명진": "oh-myung-jin", "조수행": "jo-su-haeng",
        # NC
        "박건우": "park-gun-woo", "구창모": "koo-chang-mo", "김주원": "kim-ju-won",
        "데이비슨": "davidson", "박민우": "park-min-woo", "권희동": "kwon-hee-dong",
        "김형준": "kim-hyung-jun", "김휘집": "kim-hwi-jip", "서호철": "seo-ho-chul",
        "최정원": "choi-jung-won", "테일러": "taylor", "배재환": "bae-jae-hwan",
        "임지민": "im-ji-min", "천재환": "chun-jae-hwan", "고준휘": "go-jun-hwi",
        "한석현": "han-seok-hyun", "허윤": "heo-yun", "김한별": "kim-han-byul",
        "오영수": "oh-young-soo", "김영규": "kim-young-gyu", "김진호": "kim-jin-ho",
        "손주환": "son-ju-hwan", "류진욱": "ryu-jin-wook", "임정호": "im-jung-ho",
        "이준혁": "lee-jun-hyuk",
        # 삼성
        "김성윤": "kim-sung-yun", "구자욱": "koo-ja-wook", "디아즈": "diaz",
        "최형우": "choi-hyung-woo", "김영웅": "kim-young-woong", "류지혁": "ryu-ji-hyeok",
        "이재현": "lee-jae-hyun", "김지찬": "kim-ji-chan", "강민호": "kang-min-ho",
        "박세혁": "park-se-hyuk", "오러클린": "o-rourkelin", "양창섭": "yang-chang-sub",
        "이승현": "lee-seung-hyun", "백정현": "baek-jung-hyun", "김재윤": "kim-jae-yun",
        "최지광": "choi-ji-gwang", "미야지": "miyaji", "육선엽": "yook-sun-yup",
        "장찬희": "jang-chan-hee", "배찬승": "bae-chan-seung", "임기영": "im-gi-young",
        "이승민": "lee-seung-min", "함수호": "ham-su-ho", "전병우": "jeon-byung-woo",
        "이해승": "lee-hae-seung", "김헌곤": "kim-hun-gon", "심재훈": "sim-jae-hun",
        "홍현빈": "hong-hyun-bin", "양우현": "yang-woo-hyun",
        # 한화
        "페라자": "peraza", "강백호": "kang-baek-ho", "노시환": "noh-si-hwan",
        "채은성": "chae-eun-seong", "하주석": "ha-ju-seok", "오재원": "oh-jae-won",
        "문현빈": "moon-hyun-bin", "최재훈": "choi-jae-hun", "심우준": "sim-woo-jun",
        "이도윤": "lee-do-yoon", "에르난데스": "hernandez", "왕옌청": "wang-yan-cheng",
        "황준서": "hwang-jun-seo", "김서현": "kim-seo-hyun", "윤산흠": "yoon-san-heum",
        "박상원": "park-sang-won", "조동욱": "jo-dong-wook", "박준영": "park-jun-young",
        "정우주": "jung-woo-joo", "김종수": "kim-jong-soo", "김범준": "kim-bum-jun",
        "김도빈": "kim-do-bin", "김태연": "kim-tae-yeon", "허인서": "heo-in-seo",
        "최인호": "choi-in-ho", "황영묵": "hwang-young-mook",
        # KT
        "강백호": "kang-baek-ho", "로하스": "rojas", "문보경": "moon-bo-kyung",
        "황재균": "hwang-jae-gyun", "강현우": "kang-hyun-woo", "장성우": "jang-sung-woo",
        "오윤석": "oh-yoon-seok", "사우어": "sauer", "류현인": "ryu-hyun-in",
        "이강민": "lee-gang-min", "안현민": "ahn-hyun-min", "힐리어드": "hilliard",
        "박동원": "park-dong-won", "최준용": "choi-jun-yong",
        "쿠에바스": "cuevas", "벤자민": "benjamin", "소형준": "so-hyung-jun",
        "주권": "joo-kwon", "고영표": "go-young-pyo", "박영현": "park-young-hyun",
        "백승현": "baek-seung-hyun", "김민수": "kim-min-soo",
        # LG
        "오스틴": "austin", "홍창기": "hong-chang-ki", "박해민": "park-hae-min",
        "김현수": "kim-hyun-soo", "문성주": "moon-sung-joo", "구본혁": "koo-bon-hyuk",
        "박동희": "park-dong-hee", "신민재": "shin-min-jae", "오지환": "oh-ji-hwan",
        "플루토": "pluto", "엔스": "ens", "임찬규": "im-chan-gyu",
        "함덕주": "ham-deok-joo", "정우영": "jung-woo-young", "유영찬": "yoo-young-chan",
        "김대현": "kim-dae-hyun", "박시원": "park-si-won",
        # KIA
        "나성범": "na-sung-bum", "소크라테스": "socrates", "최형우": "choi-hyung-woo-kia",
        "이창진": "lee-chang-jin", "김도영": "kim-do-young", "최원준": "choi-won-jun-kia",
        "한준수": "han-jun-soo", "박찬": "park-chan", "이우성": "lee-woo-sung",
        "양현종": "yang-hyun-jong", "네일": "nail", "정해영": "jung-hae-young",
        "윤영철": "yoon-young-chul",
        # SSG
        "최정": "choi-jung", "한유섬": "han-yoo-seom", "에레디아": "heredia",
        "고명준": "go-myung-jun", "최지훈": "choi-ji-hun", "장두성": "jang-doo-sung",
        "안상현": "ahn-sang-hyun", "노진혁": "no-jin-hyuk", "김강민": "kim-gang-min",
        "베니지아노": "veneziano", "문승원": "moon-seung-won", "오원석": "oh-won-seok",
        "정철원": "jung-chul-won",
        # 롯데
        "전준우": "jeon-jun-woo", "레이예스": "reyes", "한태양": "han-tae-yang",
        "윤동희": "yoon-dong-hee", "황성빈": "hwang-sung-bin", "나승엽": "na-seung-yub",
        "안치홍": "ahn-chi-hong", "전민재": "jeon-min-jae", "박세웅": "park-se-woong",
        "박정민": "park-jung-min",
        # 키움
        "브룩스": "brooks", "안치홍": "ahn-chi-hong", "이주형": "lee-ju-hyung",
        "김건희": "kim-gun-hee", "최주환": "choi-ju-hwan", "이형종": "lee-hyung-jong",
        "박찬혁": "park-chan-hyuk", "박한결": "park-han-gyul", "어준서": "eo-jun-seo",
        "배동현": "bae-dong-hyun", "유토": "yuto", "박정훈": "park-jung-hoon",
        "김성진": "kim-sung-jin", "김재웅": "kim-jae-woong", "박주홍": "park-ju-hong",
    }
    if name in KNOWN:
        return KNOWN[name]
    # Fallback: generate a simple slug
    return "player-" + name.replace(" ", "-")


if __name__ == "__main__":
    main()
