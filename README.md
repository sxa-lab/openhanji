[한국어](https://github.com/sxa-lab/openhanji/blob/main/README.md) | [English](https://github.com/sxa-lab/openhanji/blob/main/README.en.md) | [中文](https://github.com/sxa-lab/openhanji/blob/main/README.zh.md) | [라이선스](https://github.com/sxa-lab/openhanji/blob/main/LICENSE) | [고지사항](https://github.com/sxa-lab/openhanji/blob/main/NOTICE)

[![PyPI version](https://badge.fury.io/py/openhanji.svg)](https://badge.fury.io/py/openhanji)
[![Python Version](https://img.shields.io/pypi/pyversions/openhanji.svg)](https://pypi.org/project/openhanji/)
[![Tests](https://github.com/sxa-lab/openhanji/actions/workflows/ci.yml/badge.svg)](https://github.com/sxa-lab/openhanji/actions/workflows/ci.yml)
[![ReadTheDocs](https://img.shields.io/readthedocs/openhanji?label=ReadTheDocs)](https://openhanji.readthedocs.io/)

**한컴오피스 문서를 위한 오픈소스 Python 파서 및 변환기**

`v0.1.0`은 HWPX 문서를 구조화된 Python 문서 모델로 파싱하며 다음 형식으로 내보낼 수 있습니다:
- JSON
- Markdown
- 일반 텍스트

**유용한 용도:**
- 문서 수집과 검색
- RAG 및 NLP 워크플로
- HWPX 텍스트나 메타데이터가 필요한 백엔드 서비스

---

## 설치

```bash
pip install openhanji
```

## 빠른 시작

```python
import openhanji

doc = openhanji.open("report.hwpx")

# 문단 반복
for paragraph in doc.paragraphs:
    print(paragraph.text)

# 모든 블록 반복 (섹션을 가로질러 평탄화)
for block in doc.blocks:
    print(type(block).__name__, getattr(block, "text", ""))

# 구조화된 출력
print(doc.to_json())                        # 평탄화된 "body" 배열 (기본값)
print(doc.to_json(mode="structured"))       # 섹션별 배열
print(doc.to_markdown())
print(doc.to_text())

# 메타데이터
print(doc.metadata.title)
print(doc.metadata.author)
```

## CLI

마크다운 출력 (기본값):

```bash
openhanji extract document.hwpx
```

재귀적 일반 텍스트 추출:

```bash
openhanji extract document.hwpx --format text
```

런(run) 수준의 서식 메타데이터를 포함한 JSON 출력.

기본값이 아닌 `bold`, `italic`, `font_size`, `color` 값이 출력에 포함됩니다.

```bash
openhanji extract document.hwpx --format json
```

단축 형식 별칭:

```bash
openhanji extract document.hwpx -f json
```

JSON은 `header.xml`에 정의된 경우 Run의 `font_face`와 문단의 `align`, `style_name` 값을 포함합니다.

기본값 필드는 생략됩니다 — 단순 텍스트 Run은 다음과 같이 직렬화됩니다:

```json
{"text": "..."}
```

출력을 파일로 저장:

```bash
openhanji extract document.hwpx -o output.md
```

입력 디렉터리의 모든 `.hwpx`를 재귀적으로 변환하여 출력 디렉터리에 저장:

```bash
openhanji extract ./docs/ -o ./output/ -f markdown
```

Strict 모드는 알 수 없는 콘텐츠와 잘못된 현재 XML 파트를 건너뛰지 않고
오류를 발생시킵니다:

```bash
openhanji extract document.hwpx --strict
```

이미지 바이너리를 읽어 base64로 포함합니다.

기본적으로 바이너리 이미지 읽기는 건너뛰며 이미지가 플레이스홀더로 렌더됩니다.

```bash
openhanji extract document.hwpx --with-images
```

헤딩 분류 전략 (`auto`, `structural`, `none`).

`structural`은 구조적 헤딩 신호만 사용합니다.
`none`은 모든 문단을 `BODY`로 처리합니다.

```bash
openhanji extract document.hwpx --heading-detection structural
openhanji extract document.hwpx --heading-detection none
```

버전 출력:

```bash
openhanji --version
```

문서 메타데이터와 콘텐츠 통계를 출력합니다 — 제목, 작성자, 키워드, 날짜, 페이지 수, 문단/표/이미지 개수 등을 포함합니다:

```bash
openhanji info document.hwpx
```

---

## 지원 형식

| 형식 | 상태 | 비고 |
|------|------|------|
| `.hwpx` | 지원 | v0.1.0, ZIP + OWPML XML |

---

## 기여하기

프로젝트에 기여해 주셔서 감사드립니다. 이슈나 PR을 열어 주세요.

---

## 라이선스

Apache 2.0 © [SxA Lab](https://github.com/sxa-lab)
