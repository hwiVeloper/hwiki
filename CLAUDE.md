# hwiki — LLM Wiki Schema

이 문서는 hwiki 위키의 규칙을 정의한다. 워크플로우는 각 커맨드(`/hwiki-ingest`, `/hwiki-query`, `/hwiki-lint`)에 정의되어 있다.

## 개요

야구, 음악, 영상, 개발 등 다양한 관심사를 가진 개발자의 개인 지식 베이스.
Karpathy의 LLM Wiki 패턴을 따른다.

## 구조

- `raw/` — 원본 자료. 사람이 관리하며 LLM은 읽기만 한다.
  - `raw/articles/` — 웹 기사/블로그 클리핑 (마크다운)
  - `raw/media/` — 영상 스크립트, 팟캐스트 메모
  - `raw/notes/` — 개인 메모, 일기, 생각 정리
  - `raw/assets/` — 이미지, 첨부파일
- `wiki/` — LLM이 소유하는 위키. flat 구조.
  - `wiki/index.md` — 카테고리별 페이지 카탈로그
  - `wiki/log.md` — 시간순 작업 기록

## 위키 규칙

- **언어**: 모든 위키 페이지는 한국어로 작성한다.
- **파일명**: 영문 kebab-case (예: `shohei-ohtani.md`, `lo-fi-hip-hop.md`)
- **교차참조**: `[[wikilink]]` 스타일을 사용한다. (Obsidian 호환)
- **위치**: 모든 위키 페이지는 `wiki/` 아래 한 레벨에 위치한다. 하위 폴더 없음.

## 페이지 유형

- **source**: 원본 자료 요약. 파일명은 `source-` 접두사. (예: `source-ohtani-espn-2026.md`)
- **entity**: 인물, 팀, 아티스트, 도구 등. 이름 그대로 사용. (예: `kia-tigers.md`)
- **concept**: 개념, 장르, 기술 등. 개념명 그대로 사용. (예: `sabermetrics.md`)
- **synthesis**: 여러 자료를 종합한 분석/비교. 주제 기반 이름. (예: `ohtani-vs-ruth.md`)

## 커맨드

- `/hwiki-ingest <파일 경로> [--batch]` — 자료 입수 및 위키 통합
- `/hwiki-query <질문>` — 위키 기반 질문/답변
- `/hwiki-lint [--fix]` — 위키 건강 검진

## log.md 형식

```
## [YYYY-MM-DD] ingest|query|lint | 제목
- 변경 내용 1
- 변경 내용 2
```

최신 엔트리가 아래에 추가된다 (append-only).
