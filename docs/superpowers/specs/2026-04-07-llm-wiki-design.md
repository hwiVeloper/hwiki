# hwiki — LLM Wiki 디자인 스펙

Karpathy의 LLM Wiki 패턴을 기반으로 한, 야구/음악/영상/개발 등 다양한 관심사를 가진 개발자를 위한 개인 지식 베이스.

## 핵심 컨셉

- LLM이 위키를 작성하고 유지보수하는 persistent knowledge base
- 사람은 자료 수집과 질문, LLM은 요약/교차참조/일관성 유지 담당
- Obsidian으로 브라우징, Claude Code로 위키 관리

## 디렉토리 구조

```
hwiki/
├── .obsidian/          # Obsidian 설정
├── raw/                # 원본 자료 (사람이 관리, LLM은 읽기만)
│   ├── articles/       # 웹 클리핑 (마크다운)
│   ├── media/          # 영상 스크립트, 팟캐스트 메모
│   ├── notes/          # 개인 메모, 일기, 생각 정리
│   └── assets/         # 이미지, 첨부파일
├── wiki/               # LLM이 소유하는 위키 (flat 구조)
│   ├── index.md        # 카테고리별 페이지 카탈로그
│   └── log.md          # 시간순 작업 기록
├── CLAUDE.md           # 스키마 — 위키 규칙, 워크플로우 정의
├── .gitignore
└── docs/               # 설계 문서
```

## 위키 규칙

- **언어**: 모든 위키 페이지는 한국어
- **파일명**: 영문 kebab-case (예: `shohei-ohtani.md`, `lo-fi-hip-hop.md`)
- **교차참조**: `[[wikilink]]` 스타일 (Obsidian 호환)
- **위치**: 모든 위키 페이지는 `wiki/` 아래 flat 구조

## 페이지 유형

| 유형 | 설명 | 파일명 패턴 |
|------|------|-------------|
| source | 원본 자료 요약 | `source-*.md` |
| entity | 인물, 팀, 아티스트, 도구 등 | 이름 그대로 (예: `kia-tigers.md`) |
| concept | 개념, 장르, 기술 등 | 개념명 그대로 (예: `sabermetrics.md`) |
| synthesis | 여러 자료를 종합한 분석/비교 | 주제 기반 (예: `ohtani-vs-ruth.md`) |

## 워크플로우

### Ingest (자료 입수)

두 가지 모드 지원:

**꼼꼼형 (기본):**
1. 원본 자료 읽기
2. 핵심 내용을 사용자와 논의
3. source 요약 페이지 작성
4. 관련 entity/concept 페이지 생성 또는 업데이트
5. `wiki/index.md` 업데이트
6. `wiki/log.md`에 기록
7. git commit

**배치형 (단순 자료용):**
1. 원본 자료 읽기
2. 1~6 단계를 사용자 논의 없이 자동 처리
3. 결과 요약 보고
4. git commit

### Query (질문)

1. `wiki/index.md` 읽기
2. 관련 페이지 탐색 및 읽기
3. 답변 생성
4. 좋은 답변은 위키 페이지로 저장 (사용자 동의 시)
5. index.md, log.md 업데이트
6. git commit

### Lint (건강 검진)

주기적으로 실행:
- 페이지 간 모순 체크
- 고아 페이지 (인바운드 링크 없는 페이지) 탐지
- 누락된 교차참조 발견
- 오래된 정보 점검
- 언급만 되고 페이지가 없는 개념 탐지
- 수정 사항 반영 후 git commit

## 특수 파일

### index.md

카테고리별 페이지 카탈로그. 카테고리 예시: 야구, 음악, 영상, 개발, 출처. ingest 시마다 LLM이 업데이트.

### log.md

시간순 append-only 기록. 엔트리 형식:
```
## [YYYY-MM-DD] ingest|query|lint | 제목
```
`grep`으로 파싱 가능.

## git 관리

- `hwiki/` 루트에서 `git init`
- 작업(ingest/query/lint) 후 자동 커밋
- 커밋 메시지 형식: `ingest: 제목`, `query: 제목`, `lint: 설명`

### .gitignore

```
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/plugins/
.DS_Store
```

## 원본 자료 유형

| 폴더 | 내용 |
|------|------|
| `raw/articles/` | 웹 기사/블로그 클리핑 (마크다운) |
| `raw/media/` | 유튜브 영상 스크립트, 팟캐스트 메모 |
| `raw/notes/` | 개인 메모, 일기, 생각 정리 |
| `raw/assets/` | 이미지, 첨부파일 |

## 확장 가능성 (나중에 필요 시)

- Obsidian Dataview 플러그인 + YAML frontmatter 태그 시스템
- qmd 같은 로컬 검색 엔진 (위키가 커졌을 때)
- Marp 슬라이드 생성
