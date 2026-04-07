# hwiki Ingest

원본 자료를 읽고 위키에 통합한다.

## 사용법

```
/hwiki-ingest <파일 경로>
/hwiki-ingest <파일 경로> --batch
```

- 인자 없이 실행하면 사용자에게 파일 경로를 물어본다.
- `--batch` 플래그가 있으면 배치형으로 처리한다.

## 꼼꼼형 (기본)

1. `$ARGUMENTS`에서 파일 경로를 파싱한다. `--batch` 플래그 여부를 확인한다.
2. 해당 파일을 읽는다.
3. 핵심 내용과 주요 takeaway를 사용자에게 보여주고 논의한다.
4. 사용자와 논의가 끝나면 다음을 수행한다:
   - `wiki/source-*.md` 요약 페이지를 작성한다.
   - 관련 entity/concept 페이지를 생성하거나 업데이트한다.
   - `wiki/index.md`를 업데이트한다.
   - `wiki/log.md`에 `## [YYYY-MM-DD] ingest | 자료 제목` 형식으로 기록을 추가한다.
5. 변경된 파일을 git commit한다. 메시지: `ingest: [자료 제목]`

## 배치형 (`--batch`)

1. `$ARGUMENTS`에서 파일 경로를 파싱한다.
2. 해당 파일을 읽는다.
3. 사용자 논의 없이 자동으로 처리한다:
   - `wiki/source-*.md` 요약 페이지를 작성한다.
   - 관련 entity/concept 페이지를 생성하거나 업데이트한다.
   - `wiki/index.md`를 업데이트한다.
   - `wiki/log.md`에 기록을 추가한다.
4. 처리 결과를 요약 보고한다.
5. git commit한다. 메시지: `ingest: [자료 제목]`

## 위키 규칙 (CLAUDE.md 참조)

- 모든 위키 페이지는 한국어로 작성한다.
- 파일명은 영문 kebab-case (예: `source-ohtani-espn-2026.md`)
- 교차참조는 `[[wikilink]]` 스타일을 사용한다.
- 모든 위키 페이지는 `wiki/` 아래 flat 구조로 위치한다.
- 페이지 유형: source(`source-*`), entity(이름 그대로), concept(개념명 그대로), synthesis(주제 기반)
