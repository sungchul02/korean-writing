# korean-writing

한국어 글(학술 논문, 국문 요약, 보고서, README 등)을 쓰거나 고칠 때 쓰는 Claude Code 스킬이다. 문장 규칙, 끝맺음과 수치 표기, 쓰지 않는 표현, 서술 순서, 용어 일관성, 단락·장 나눔, 기준 원고에 맞추는 방법을 담았다.

## 설치

이 저장소를 `~/.claude/skills/korean-writing/`에 둔다(`SKILL.md`와 `scripts/`). 국문 원고·보고서 작성, 원고 수정, 문체 다듬기를 요청하면 Claude Code가 이 스킬을 불러 쓴다.

## 생성 흔적 점검 (`scripts/clean_traces.py`)

글을 넘기기 전에 보이지 않는 문자(폭 없는 공백, 태그 문자, 변형 선택자 등), 도구 꼬리말, docx·PDF 메타데이터를 점검하고 정리한다.

- `python scripts/clean_traces.py 파일`: 보고만 한다.
- `python scripts/clean_traces.py 파일 --fix [--author 이름]`: 원본은 두고 `파일명 (정리).확장자`를 만든다. 지원 형식은 txt, md, docx, pdf.

Claude의 통계적 텍스트 워터마크(단어 선택에 들어가는 SynthID-Text 방식)는 숨은 문자가 아니므로 이 스크립트로 지워지지 않으며, 지우는 기능을 넣지 않는다. AI 사용 고지 문장도 지우지 않는다. 자세한 내용은 `SKILL.md` 10절.

---

A Claude Code skill for writing and revising Korean text (academic papers, reports, READMEs): sentence rules, endings and number formatting, phrases to avoid, section order, terminology consistency, and paragraph structure. It also ships `scripts/clean_traces.py`, which reports and removes invisible characters, tool footers and docx/PDF metadata (it does not and cannot remove Claude's statistical text watermark). Install by placing this repository at `~/.claude/skills/korean-writing/`.
