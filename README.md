[한국어](README.md) | [English](README.en.md) | [中文](README.zh.md) | [라이선스](LICENSE) | [고지사항](NOTICE)

**한컴오피스 HWPX 문서를 위한 오픈소스 Python 파서**

`v0.1.0` 은 HWPX 문서를 파싱하는 Python 패키지입니다. 문서 내용을 `Document` 로 읽고, JSON, Markdown, 또는 일반 텍스트로 출력합니다.

최상위 `doc.paragraphs`, `doc.tables`, `doc.images` 는 문서 본문의 최상위
항목만 노출합니다. `doc.blocks` 는 모든 섹션에 걸쳐 평탄화된 블록 목록입니다.
중첩 표와 이미지는 각 셀의 `cell.blocks` 안에 보존되며,
`cell.text` 는 셀 전체 내용을 재귀적으로 평탄화한 텍스트를 제공합니다.

---

## 설치

```bash
pip install openhanji
```

## 사용법 시작

```python
import openhanji

doc = openhanji.open("정부보고서.hwpx")

#문단 순회
for paragraph in doc.paragraphs:
    print(paragraph.text)

#전체 블록 순회 (모든 섹션에 걸쳐 평탄화)
for block in doc.blocks:
    print(type(block).__name__, getattr(block, "text", ""))

#구조화된 출력
print(doc.to_json())                        #플랫 "body" 배열 (기본값)
print(doc.to_json(mode="structured"))       #섹션별 배열
print(doc.to_markdown())
print(doc.to_text())

#메타데이터
print(doc.metadata.title)
print(doc.metadata.author)
```

## CLI

```bash
#마크다운 (기본값) - 제목과 단순 표는 Markdown, 복잡한 표는 HTML 로 보존
openhanji extract 문서.hwpx
```

```bash
#텍스트 - 중첩 표를 포함한 재귀적 일반 텍스트 추출
openhanji extract 문서.hwpx --format text
```

```bash
#json - 완전한 데이터; 기본값이 아닌 경우에만 bold/italic/font_size/color 포함
openhanji extract 문서.hwpx --format json
```

```bash
#짧은 형식 별칭
openhanji extract 문서.hwpx -f json
```

`header.xml` 에 값이 설정된 경우 JSON 출력에 `font_face`, 문단
`align`, `style_name` 이 포함됩니다. 기본값 필드는 생략됩니다.

```bash
#파일로 저장
openhanji extract 문서.hwpx -o output.md
```

```bash
#디렉터리 모드 - 디렉터리 안의 모든 .hwpx 를 재귀적으로 찾아 출력 디렉터리에 변환
openhanji extract ./문서들/ -o ./output/ -f markdown
```

```bash
#strict 모드 - 알 수 없는 콘텐츠를 건너뛰지 않고 오류로 처리
openhanji extract 문서.hwpx --strict
```

```bash
#with-images - 이미지 바이너리를 읽어 base64로 포함 (기본값: 건너뜀, 플레이스홀더로 렌더링)
openhanji extract 문서.hwpx --with-images
```

```bash
#heading-detection - 제목 감지 전략 (기본값: auto)
openhanji extract 문서.hwpx --heading-detection structural  #구조적 신호만 사용
openhanji extract 문서.hwpx --heading-detection none        #모든 단락을 BODY로 처리
```

```bash
#버전 확인
openhanji --version
```

```bash
#메타데이터 - 제목/작성자/주제/키워드/날짜/페이지/문단·표·이미지 개수 출력
openhanji info 문서.hwpx
```

---

## 지원 형식

| 형식 | 상태 | 비고 |
|------|------|------|
| `.hwpx` | 지원 | v0.1.0, ZIP + OWPML XML |

---

## 기여하기

프로젝트에 기여를 환영합니다. 이슈나 PR을 열어주세요.

---

## 라이선스

Apache 2.0 © [SxA Lab](https://github.com/sxa-lab)
