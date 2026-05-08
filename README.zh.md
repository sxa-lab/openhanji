[한국어](README.md) | [English](README.en.md) | [中文](README.zh.md) | [许可证](LICENSE) | [声明](NOTICE)

**用于 Hancom Office HWPX 文档的开源 Python 解析器**

`v0.1.0` 是一个用于解析 HWPX 文档的 Python 包。它将文档读取为 `Document` 对象，并输出 JSON、Markdown 或纯文本。

顶层 `doc.paragraphs`、`doc.tables`、`doc.images` 只暴露正文中的顶层块。
`doc.blocks` 是跨所有章节平铺的全部块列表。嵌套表格和图片会保留在所属单元格的
`cell.blocks` 中，而 `cell.text` 提供该单元格全部内容的递归纯文本摘要。

---

## 安装

```bash
pip install openhanji
```

## 快速开始

```python
import openhanji

doc = openhanji.open("report.hwpx")

#遍历段落
for paragraph in doc.paragraphs:
    print(paragraph.text)

#遍历所有块（跨章节平铺）
for block in doc.blocks:
    print(type(block).__name__, getattr(block, "text", ""))

#结构化输出
print(doc.to_json())                        #平铺 "body" 数组（默认）
print(doc.to_json(mode="structured"))       #按章节分组的数组
print(doc.to_markdown())
print(doc.to_text())

#元数据
print(doc.metadata.title)
print(doc.metadata.author)
```

## CLI

```bash
#markdown（默认）- 标题和简单表格使用 Markdown，复杂表格回退为 HTML
openhanji extract document.hwpx
```

```bash
#text - 递归纯文本提取，包含嵌套表格内容
openhanji extract document.hwpx --format text
```

```bash
#json - 完整数据；仅在非默认时包含 bold/italic/font_size/color
openhanji extract document.hwpx --format json
```

```bash
#短格式别名
openhanji extract document.hwpx -f json
```

JSON 中默认值字段被省略 — 纯文本 Run 仅序列化为 `{"text": "..."}`.
设置了 `header.xml` 值时，输出中会包含 `font_face`、`align`、`style_name`。

```bash
#保存到文件
openhanji extract document.hwpx -o output.md
```

```bash
#目录模式 - 递归转换输入目录下的所有 .hwpx 文件并写入输出目录
openhanji extract ./docs/ -o ./output/ -f markdown
```

```bash
#严格模式 - 遇到未知内容时直接报错，而不是跳过
openhanji extract document.hwpx --strict
```

```bash
#with-images - 读取并以 base64 内联嵌入图片二进制（默认跳过读取，图片渲染为占位符）
openhanji extract document.hwpx --with-images
```

```bash
#heading-detection - 标题检测策略（默认：auto）
openhanji extract document.hwpx --heading-detection structural  #仅使用结构信号
openhanji extract document.hwpx --heading-detection none        #所有段落均为 BODY
```

```bash
#查看版本
openhanji --version
```

```bash
#元数据 - 输出标题、作者、主题、关键词、日期、页数以及段落/表格/图片数量
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
