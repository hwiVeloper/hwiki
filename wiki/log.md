# hwiki Log

## [2026-04-07] init | hwiki 초기 세팅
- 디렉토리 구조 생성 (raw/, wiki/)
- index.md, log.md 초기화
- CLAUDE.md 스키마 작성

## [2026-04-08] ingest | 두산 베어스 2026 시즌 초반 8경기 기록 일괄 입수
- source 페이지 8개 생성 (03.29~04.05 경기)
- entity 페이지 생성: doosan-bears, nc-dinos, samsung-lions, hanwha-eagles (팀 4개)
- entity 페이지 생성: 두산 선수 15명 (양의지, 카메론, 박준순, 안재석, 박찬호, 정수빈, 양석환, 강승호, 김민석, 박지훈, 잭로그, 플렉센, 타무라, 김택연, 곽빈)
- entity 페이지 생성: 상대팀 선수 11명 (박건우, 구창모, 김성윤, 구자욱, 디아즈, 최형우, 페라자, 강백호, 노시환, 채은성, 하주석)
- concept 페이지 생성: kbo-2026-season
- index.md 업데이트

## [2026-04-08] refactor | wiki 폴더 구조 정리
- 야구 관련 페이지를 wiki/baseball/kbo/ 하위로 재배치
- teams/ (팀 4개), players/ (선수 26명), games/ (경기 기록 8개) 분리
- concept 페이지는 kbo/ 루트에 유지
- index.md, CLAUDE.md 업데이트

## [2026-04-08] query | 최민석 선수 페이지 추가
- entity 페이지 생성: choi-min-seok (선발투수)
- 4/2 삼성전 6이닝 무자책 호투 기록 반영
- index.md 업데이트

## [2026-04-08] ingest | LLM Wiki 패턴 세미나 자료
- source 페이지 생성: source-llm-wiki-seminar (PDF 15p + 인포그래픽)
- concept 페이지 생성: llm-wiki (LLM Wiki 패턴 개념 정리)
- index.md 업데이트 (개발 카테고리 추가)

## [2026-04-09] ingest | KBO 2026 시즌 전체 재구성 (3/28~4/8)
- raw/articles/kbo/ 기반 전 구단 데이터로 wiki 재구성
- source 페이지 50개 생성 (10개 날짜, 전 경기)
- 팀 entity 10개 생성 (두산, NC, 삼성, 한화, KT, LG, KIA, SSG, 롯데, 키움)
- 선수 entity 326개 생성 (전 구단 타자 + 투수)
- kbo-2026-season concept 페이지 업데이트 (순위표 포함)
- index.md 전면 업데이트
- 스크립트 생성: scripts/rebuild_kbo_wiki.py

## [2026-04-14] ingest | KBO 자동 수집 (2026-04-11 ~ 2026-04-12)
- 신규 경기 10개 반영 (2일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-15] ingest | KBO 자동 수집 (2026-04-14)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-15] ingest | KBO 위키 전면 재구성 (raw/articles/kbo/ 기반)
- raw/articles/kbo/2026/ 70경기 원본을 파싱해 wiki/baseball/kbo/ 하위 전면 재생성
- teams/ 10팀: 성적표·로스터 집계 통계 재빌드 (타자 타율/장타 관련, 투수 ERA/탈삼진 등)
- players/ 359명: 파일명 컨벤션 `{team}-{name_romanized}.md` 일원화, 모든 경기별 지표 수록
- games/ 70개: source 페이지 표 형식 통일, 신규 wikilink 적용
- kbo-2026-season.md: 순위표·위키 구조·파일명 컨벤션 문서화
- index.md: 신규 슬러그로 전면 재빌드
- 같은 한글명 다팀 등장 5건(손아섭·최원준·박지훈·김민석·화이트)에 동명이인/이적 주의 박스 삽입
- 깨진 wikilink 0건 (dev 예시 문구 제외)

## [2026-04-16] ingest | KBO 자동 수집 (2026-04-15)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-17] ingest | KBO 자동 수집 (2026-04-16)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-18] ingest | KBO 자동 수집 (2026-04-17)
- 신규 경기 2개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-19] ingest | KBO 자동 수집 (2026-04-18)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-20] ingest | KBO 자동 수집 (2026-04-19)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-22] ingest | KBO 자동 수집 (2026-04-21)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-23] ingest | KBO 자동 수집 (2026-04-22)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-24] ingest | KBO 자동 수집 (2026-04-23)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-25] ingest | KBO 자동 수집 (2026-04-24)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-26] ingest | KBO 자동 수집 (2026-04-25)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-27] ingest | KBO 자동 수집 (2026-04-26)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-29] ingest | KBO 자동 수집 (2026-04-28)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-04-30] ingest | KBO 자동 수집 (2026-04-29)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-05-01] ingest | KBO 자동 수집 (2026-04-30)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-05-02] ingest | KBO 자동 수집 (2026-05-01)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-05-03] ingest | KBO 자동 수집 (2026-05-02)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-05-04] ingest | KBO 자동 수집 (2026-05-03)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-05-06] ingest | KBO 자동 수집 (2026-05-05)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-05-07] ingest | KBO 자동 수집 (2026-05-06)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-05-08] ingest | KBO 자동 수집 (2026-05-07)
- 신규 경기 4개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-05-09] ingest | KBO 자동 수집 (2026-05-08)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

## [2026-05-10] ingest | KBO 자동 수집 (2026-05-09)
- 신규 경기 5개 반영 (1일치)
- games / teams / players / kbo-2026-season / index 재생성

<!-- last-kbo-ingest-date: 2026-05-09 -->
