[한국어](https://github.com/sxa-lab/openhanji/blob/main/README.md) | [English](https://github.com/sxa-lab/openhanji/blob/main/README.en.md) | [中文](https://github.com/sxa-lab/openhanji/blob/main/README.zh.md) | [许可证](https://github.com/sxa-lab/openhanji/blob/main/LICENSE) | [声明](https://github.com/sxa-lab/openhanji/blob/main/NOTICE)

**用于 Hancom Office 文档的开源 Python 解析器和转换器**

`v0.1.0` 将 HWPX 文档解析为结构化的 Python 文档模型，可导出为：
- JSON
- Markdown
- 纯文本

**适用场景：**
- 文档摄取与搜索
- RAG 与 NLP 工作流
- 需要 HWPX 文本或元数据的后端服务

---

## 安装

```bash
pip install openhanji
```

## 快速开始

```python
import openhanji

doc = openhanji.open("report.hwpx")

# 遍历段落
for paragraph in doc.paragraphs:
    print(paragraph.text)

# 遍历所有块（跨章节平铺）
for block in doc.blocks:
    print(type(block).__name__, getattr(block, "text", ""))

# 结构化输出
print(doc.to_json())                        # 平铺的 "body" 数组（默认）
print(doc.to_json(mode="structured"))       # 按章节分组的数组
print(doc.to_markdown())
print(doc.to_text())

# 元数据
print(doc.metadata.title)
print(doc.metadata.author)
```

## CLI

Markdown 输出（默认）：

```bash
openhanji extract document.hwpx
```

递归式纯文本提取：

```bash
openhanji extract document.hwpx --format text
```

包含运行级别格式元数据的 JSON 输出。

非默认的 `bold`、`italic`、`font_size` 和 `color` 值会包含在输出中。

```bash
openhanji extract document.hwpx --format json
```

短格式别名：

```bash
openhanji extract document.hwpx -f json
```

当在 `header.xml` 中定义时，JSON 会包含 run 上解析后的 `font_face`，以及段落上的 `align` 和 `style_name` 值。

默认值字段会被省略 — 纯文本 run 序列化为：

```json
{"text": "..."}
```

将输出保存到文件：

```bash
openhanji extract document.hwpx -o output.md
```

递归地将输入目录下的每个 `.hwpx` 转换到输出目录：

```bash
openhanji extract ./docs/ -o ./output/ -f markdown
```

Strict 模式在遇到未知内容和格式错误的现有 XML 部件时抛出错误，而不是跳过：

```bash
openhanji extract document.hwpx --strict
```

读取并以 base64 嵌入图片二进制。

默认情况下会跳过二进制图片读取，图片以占位符渲染。

```bash
openhanji extract document.hwpx --with-images
```

标题分类策略 (`auto`, `structural`, `none`)。

`structural` 仅使用结构性标题信号。

`none` 将所有段落视为 `BODY`。

```bash
openhanji extract document.hwpx --heading-detection structural
openhanji extract document.hwpx --heading-detection none
```

打印版本：

```bash
openhanji --version
```

打印文档元数据和内容统计信息，包括标题、作者、关键词、日期、页数，以及段落/表格/图片计数：

```bash
openhanji info document.hwpx
```

---

## 格式支持

| 格式 | 状态 | 说明 |
|------|------|------|
| `.hwpx` | 已支持 | v0.1.0，ZIP + OWPML XML |

---

## 贡献

欢迎参与贡献。请提交 Issue 或 PR。

---

## 许可证

Apache 2.0 © [SxA Lab](https://github.com/sxa-lab)
