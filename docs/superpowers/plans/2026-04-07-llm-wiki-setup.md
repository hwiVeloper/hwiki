# hwiki LLM Wiki 초기 세팅 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Karpathy LLM Wiki 패턴에 따른 개인 지식 베이스 초기 구조를 세팅한다.

**Architecture:** `raw/`(원본 자료) + `wiki/`(LLM 관리 위키, flat) + `CLAUDE.md`(스키마) 3계층 구조. git으로 버전 관리. Obsidian vault로 브라우징.

**Tech Stack:** Markdown, Git, Obsidian, Claude Code

---

### Task 1: Git 초기화 및 .gitignore

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: git 저장소 초기화**

Run: `cd /Users/hwiveloper/Developer/hwiki/hwiki && git init`
Expected: `Initialized empty Git repository`

- [ ] **Step 2: .gitignore 생성**

```
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/plugins/
.DS_Store
```

- [ ] **Step 3: 초기 커밋**

```bash
git add .gitignore .obsidian/app.json .obsidian/appearance.json .obsidian/community-plugins.json .obsidian/core-plugins.json .obsidian/graph.json
git commit -m "init: git 저장소 초기화 및 obsidian 설정"
```

Expected: 커밋 성공, 6개 파일

---

### Task 2: 디렉토리 구조 생성

**Files:**
- Create: `raw/articles/.gitkeep`
- Create: `raw/media/.gitkeep`
- Create: `raw/notes/.gitkeep`
- Create: `raw/assets/.gitkeep`
- Create: `wiki/` (index.md, log.md는 Task 3에서)

- [ ] **Step 1: raw 디렉토리 구조 생성**

```bash
mkdir -p raw/articles raw/media raw/notes raw/assets wiki
touch raw/articles/.gitkeep raw/media/.gitkeep raw/notes/.gitkeep raw/assets/.gitkeep
```

git은 빈 디렉토리를 추적하지 않으므로 `.gitkeep` 파일을 넣는다.

- [ ] **Step 2: 커밋**

```bash
git add raw/
git commit -m "init: raw 디렉토리 구조 생성 (articles, media, notes, assets)"
```

---

### Task 3: wiki/index.md 생성

**Files:**
- Create: `wiki/index.md`

- [ ] **Step 1: index.md 작성**

```markdown
# hwiki Index

## 야구

## 음악

## 영상

## 개발

## 기타

## 출처
```

빈 카테고리 틀. 자료 ingest 시 LLM이 항목을 추가한다.

- [ ] **Step 2: 커밋**

```bash
git add wiki/index.md
git commit -m "init: wiki/index.md 카테고리 틀 생성"
```

---

### Task 4: wiki/log.md 생성

**Files:**
- Create: `wiki/log.md`

- [ ] **Step 1: log.md 작성**

```markdown
# hwiki Log

## [2026-04-07] init | hwiki 초기 세팅
- 디렉토리 구조 생성 (raw/, wiki/)
- index.md, log.md 초기화
- CLAUDE.md 스키마 작성
```

- [ ] **Step 2: 커밋**

```bash
git add wiki/log.md
git commit -m "init: wiki/log.md 작업 기록 초기화"
```

---

### Task 5: CLAUDE.md 스키마 작성

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md 작성**

```markdown
# hwiki — LLM Wiki Schema

이 문서는 hwiki 위키의 규칙과 워크플로우를 정의한다. LLM은 이 스키마에 따라 위키를 관리한다.

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

## 워크플로우

### Ingest (자료 입수)

사용자가 `raw/`에 자료를 넣고 ingest를 요청하면:

**꼼꼼형 (기본 — 중요하거나 복잡한 자료):**
1. 원본 자료를 읽는다.
2. 핵심 내용과 주요 takeaway를 사용자에게 보여주고 논의한다.
3. `wiki/source-*.md` 요약 페이지를 작성한다.
4. 관련 entity/concept 페이지를 생성하거나 업데이트한다.
5. `wiki/index.md`를 업데이트한다.
6. `wiki/log.md`에 기록을 추가한다.
7. 변경된 파일을 git commit한다. 메시지: `ingest: [자료 제목]`

**배치형 (단순 자료):**
1. 원본 자료를 읽는다.
2. 위 3~6 단계를 사용자 논의 없이 자동 처리한다.
3. 처리 결과를 요약 보고한다.
4. git commit한다.

사용자가 모드를 지정하지 않으면 꼼꼼형으로 진행한다.

### Query (질문)

사용자가 위키에 대해 질문하면:
1. `wiki/index.md`를 읽어 관련 페이지를 파악한다.
2. 관련 페이지들을 읽고 답변을 생성한다.
3. 답변이 위키 페이지로 저장할 가치가 있으면 사용자에게 제안한다.
4. 저장 시 synthesis 페이지를 생성하고 index.md, log.md를 업데이트한다.
5. git commit한다. 메시지: `query: [질문 주제]`

### Lint (건강 검진)

사용자가 lint를 요청하면:
1. 모든 위키 페이지를 스캔한다.
2. 다음을 점검한다:
   - 페이지 간 모순되는 정보
   - 고아 페이지 (다른 페이지에서 링크되지 않는 페이지)
   - 누락된 교차참조 (`[[link]]`로 연결되어야 할 관련 페이지)
   - 언급만 되고 페이지가 없는 개념/엔티티
   - 오래된 정보
3. 발견된 문제를 보고하고 수정을 제안한다.
4. 승인된 수정 사항을 반영한다.
5. git commit한다. 메시지: `lint: [수정 내용 요약]`

## log.md 형식

엔트리는 다음 형식을 따른다:

```
## [YYYY-MM-DD] ingest|query|lint | 제목
- 변경 내용 1
- 변경 내용 2
```

최신 엔트리가 아래에 추가된다 (append-only).
```

- [ ] **Step 2: 커밋**

```bash
git add CLAUDE.md
git commit -m "init: CLAUDE.md 위키 스키마 작성"
```

---

### Task 6: docs 디렉토리 커밋 및 최종 확인

**Files:**
- Existing: `docs/superpowers/specs/2026-04-07-llm-wiki-design.md`
- Existing: `docs/superpowers/plans/2026-04-07-llm-wiki-setup.md`

- [ ] **Step 1: docs 커밋**

```bash
git add docs/
git commit -m "docs: 디자인 스펙 및 구현 계획 추가"
```

- [ ] **Step 2: 최종 확인**

Run: `tree -I '.obsidian|.git' /Users/hwiveloper/Developer/hwiki/hwiki/`

Expected output:
```
hwiki/
├── CLAUDE.md
├── docs/
│   └── superpowers/
│       ├── plans/
│       │   └── 2026-04-07-llm-wiki-setup.md
│       └── specs/
│           └── 2026-04-07-llm-wiki-design.md
├── raw/
│   ├── articles/
│   │   └── .gitkeep
│   ├── assets/
│   │   └── .gitkeep
│   ├── media/
│   │   └── .gitkeep
│   └── notes/
│       └── .gitkeep
└── wiki/
    ├── index.md
    └── log.md
```

- [ ] **Step 3: git log 확인**

Run: `git log --oneline`

Expected: 6개 커밋이 순서대로 보임
