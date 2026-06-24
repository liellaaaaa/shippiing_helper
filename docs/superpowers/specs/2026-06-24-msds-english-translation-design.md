# MSDS 英文生成翻译覆盖率提升方案

**日期**：2026-06-24
**状态**：已批准
**目标**：将英文 MSDS 生成翻译覆盖率从 ~70-80% 提升至 ~95%+

---

## 1. 背景与问题

`generate_msds_english()` 当前依赖 `msds_english_template.json` 的 `fixed_texts` 做精确匹配翻译，但存在以下问题：

1. **覆盖度不足**：Section 4-16 大量段落内容（急救措施、操作处置、废弃物处置等）未翻译
2. **精确匹配失败**：部分 key 因 encoding/空格/标点差异无法匹配原文（如 "戴化学护目镜" vs "戴化学护目镜" 含多余空格）
3. **新内容无对应条目**：用户编辑的新成分或自定义内容没有翻译

用户期望：在 Phase 2 文档编辑中选择"English MSDS"时，生成可直接使用的英文文档。

---

## 2. 翻译流程（三层 Fallback）

```
原始中文 MSDS 文档
       ↓
Step 1: 精确匹配翻译
  → _translation_mapping（按 key 长度降序排列）
  → 来源：msds_english_template.json 的 fixed_texts + section_titles + sectionN_fields
       ↓ 匹配失败
Step 2: 模糊匹配翻译
  → 对原文和 key 都执行 normalize() 归一化后再匹配
  → 归一化规则：
      - 全角数字 → 半角（１→1）
      - 全角字母 → 半角
      - 去除多余连续空格
      - 全角标点 → 半角标点（：→:,，→,）
      - 去除前后空格
       ↓ 匹配失败
Step 3: 离线机翻
  → argostranslate（中文→英文，约 50MB 模型，完全离线）
       ↓ 翻译失败
Step 4: 保留原文（当前行为，不报错）
```

---

## 3. 核心实现

### 3.1 normalize() 归一化函数

```python
def _normalize(self, text: str) -> str:
    """
    归一化文本：全角→半角、去除多余空格、标点标准化
    用于模糊匹配阶段，解决 encoding/空格/标点差异导致的匹配失败
    """
    import unicodedata
    import re

    # 1. Unicode 归一化（NFKC 规范化，将全角字符转为兼容半角）
    text = unicodedata.normalize('NFKC', text)

    # 2. 全角数字 → 半角（UNICODE 范围）
    text = text.translate(str.maketrans(
        '０１２３４５６７８９',
        '0123456789'
    ))

    # 3. 去除多余连续空格（保留单词间单空格）
    text = re.sub(r'\s+', ' ', text)

    # 4. 去除前后空格
    text = text.strip()

    return text
```

### 3.2 模糊匹配（fuzzy_match）

在 `_build_translation_mapping()` 中，对每个 key 同时注册：
- 原始 key（精确匹配用）
- normalize 后的 key（模糊匹配用）

```python
# 示例
原始: "戴化学护目镜"          → 翻译: "Wear chemical safety goggles"
模糊: "戴化学护目镜" (normalize后) → 同一翻译结果
```

### 3.3 argostranslate 集成

**安装**：`pip install argostranslate`

**模型自动下载**：首次翻译时自动下载中文→英文模型包（约 50MB）。

```python
def _ensure_argos_model(self):
    """确保 argostranslate 中文→英文模型已下载"""
    import argostranslate
    installed = {p.code for p in argostranslate.package.get_installed_packages()}
    if "zh_en" not in installed:
        argostranslate.package.update()
        available = argostranslate.package.get_available_packages()
        zh_en_pkg = next(
            (p for p in available if p.source_lang == "zh" and p.target_lang == "en"),
            None
        )
        if zh_en_pkg:
            argostranslate.package.install(zh_en_pkg)

def _translate_with_argos(self, text_cn: str) -> str:
    """使用 argostranslate 翻译中文→英文"""
    try:
        from argostranslate import translate
        result = translate.translate(text_cn, "zh", "en")
        return result
    except Exception:
        return text_cn  # fallback: 保留原文
```

### 3.4 改进的 _translate_paragraph_text()

```python
def _translate_paragraph_text(self, text: str) -> str:
    """
    三层 fallback 翻译：
    1. 精确匹配（_translation_mapping）
    2. 模糊匹配（normalize 后）
    3. 离线机翻（argostranslate）
    """
    if not text:
        return text

    # Step 1: 精确匹配
    for cn, en in self._translation_mapping:
        if cn in text:
            text = text.replace(cn, en)

    # 检查是否还有残留中文（简单判断：是否含中文基本汉字）
    import re
    if not re.search(r'[一-鿿]', text):
        return text  # 已全部翻译

    # Step 2: 模糊匹配（对未翻译段落再次匹配）
    normalized = self._normalize(text)
    for cn, en in self._translation_mapping:
        cn_norm = self._normalize(cn)
        if cn_norm != cn and cn_norm in normalized:
            normalized = normalized.replace(cn_norm, en)
    if not re.search(r'[一-鿿]', normalized):
        return normalized

    # Step 3: argostranslate 机翻
    # 按句子分割，逐句翻译，避免超长文本
    return self._translate_with_argos(text)
```

---

## 4. msds_english_template.json 补全条目

以下 `fixed_texts` 条目基于 `test_english_final.txt` 分析，需要**确认已存在或新增**的条目。

**已存在于 template、无需重复添加的条目**（但因段落含前缀导致精确匹配失效，主要靠模糊匹配层解决）：
- `戴化学护目镜` → `Wear chemical safety goggles`（已在 line 241）
- `戴防渗橡胶手套` → `Wear impermeable rubber gloves`（已在 line 242）
- `使用符合工业卫生标准的衣服` → `Wear clothing meeting industrial hygiene standards`（已在 line 243）
- `操作处置：保持工作场所通风良好...` 长句（已在 fixed_texts）
- `若超过职业暴露限制，需佩戴呼吸防护设备`（已在 fixed_texts）

| 类别 | 中文原文 | 英文翻译 |
|------|----------|----------|
| Section 4 | 皮肤接触：脱去污染衣服，用清水彻底冲洗皮肤，必要时就医。 | Skin Contact: Remove contaminated clothing, rinse skin thoroughly with water, seek medical advice if necessary. |
| Section 4 | 眼睛接触：提起眼睑，用大量清水清洗，必要时就医。 | Eye Contact: Lift eyelids and rinse with plenty of water, seek medical advice if necessary. |
| Section 4 | 吸入: 如果吸入，请将患者移到新鲜空气处。必要时就医。 | Inhalation: If inhaled, move patient to fresh air. Seek medical advice if necessary. |
| Section 4 | 食入: 漱口，禁止催吐。立即就医。 | Ingestion: Rinse mouth, do not induce vomiting. Seek immediate medical attention. |
| Section 4 | 对保护施救者的忠告：将患者转移到安全的场所。咨询医生。 | Advice for Rescuers: Move patient to a safe place. Consult a doctor. |
| Section 6 | 避免溢出物接触进入土壤, 河流, 下水道和污水管道。 | Avoid contact with soil, rivers, sewers and wastewater. |
| Section 6 | 如产品已经导致环境污染（下水道，水道，土壤或空气），请通知有关当局。 | If the product has caused environmental pollution (sewers, waterways, soil or air), notify relevant authorities. |
| Section 7 | 操作处置：保持工作场所通风良好，禁止使用易产生火花的工具，远离火源热源，工作场所严禁吸烟。操作时工作人员应该佩戴自吸过滤式防毒面罩，佩戴防护手套。 | Handling: Keep workplace well ventilated, do not use tools that produce sparks, keep away from fire and heat sources, no smoking in the workplace. Operators should wear self-priming filter gas mask and protective gloves. |
| Section 7 | 储存：于阴凉、干燥、有合理通风的区域，防止阳光直射。保持容器密封，应备有泄漏应急处理设备和合适的收容材料。 | Storage: Store in cool, dry, well-ventilated area, avoid direct sunlight. Keep container tightly closed, leak emergency equipment and suitable containment materials should be available. |
| Section 8 | 工作现场禁止吸烟，进食和饮水，工作完毕，沐浴更衣，注意个人清洁卫生 | No smoking, eating or drinking in the workplace; bathe and change clothes after work; pay attention to personal hygiene |
| Section 10 | 稳定性：正常环境温度下储存和使用，本品稳定。 | Stability: This product is stable when stored and used at normal ambient temperature. |
| Section 12 | 生态毒性： | Ecotoxicity: |
| Section 13 | 不得采用排放到下水道的方式废弃处置本品。 | Do not dispose of this product by discharging to sewers. |
| Section 16 | 按照《化学品安全技术说明书，内容和专业顺序》GB/T16483-2005标准，对前版SDS进行修订， | Revised the previous SDS according to GB/T16483-2005 standard for Chemical Safety Technical Data Sheet content and professional sequence |
| Section 16 | 下列法律法规和标准，对化学品的使用、储存、运输、装卸、分类和标识等方面作了相应的规定： | The following laws, regulations and standards have made corresponding provisions for the use, storage, transport, loading and unloading, classification and labeling of chemicals: |
| 主标题 | 化学品安全资料说明书 | MATERIAL SAFETY DATA SHEET |

---

## 5. 文件修改清单

### backend/app/services/msds_generator_service.py

| 新增/修改 | 内容 |
|-----------|------|
| 新增 | `_normalize(text: str) -> str` |
| 新增 | `_ensure_argos_model()` |
| 新增 | `_translate_with_argos(text: str) -> str` |
| 修改 | `_build_translation_mapping()` — 同时注册原始 key 和 normalize key |
| 修改 | `_translate_paragraph_text()` — 三层 fallback 逻辑 |

### references/msds_english_template.json

| 操作 | 内容 |
|------|------|
| 修改 | `fixed_texts` 新增 ~25 条缺失条目（上表所列） |
| 新增 | `normalized_keys` 映射（normalize 后的 key → 英文翻译） |

### backend/requirements.txt 或 pyproject.toml

| 依赖 | 说明 |
|------|------|
| `argostranslate` | 离线翻译库 |

---

## 6. 验证方案

### 6.1 翻译覆盖率检查

生成英文 MSDS 后，检查以下指标：
- 残留中文字符数（目标：< 5%）
- Section 4-16 每节是否有残留中文（目标：0 处整段未翻译）

### 6.2 边界测试用例

| 测试内容 | 预期结果 |
|----------|----------|
| MSDS 中含 "化学品安全资料说明书" | 翻译为 "MATERIAL SAFETY DATA SHEET" |
| MSDS 中含 "戴化学护目镜"（有多余空格） | 模糊匹配成功，翻译为 "Wear chemical safety goggles" |
| MSDS 中含用户自定义成分名（如 "新型柔软剂"） | argostranslate 翻译为英文 |
| MSDS 中仅含英文（如 "Product Name:"） | 不翻译，保留原文 |

### 6.3 性能测试

- argostranslate 首次翻译耗时（模型加载）
- 1000 段落翻译总耗时

---

## 7. 不在此方案范围

- 创建纯英文 MSDS 模板文件（独立 .docx）
- 前端 UI 改动
- 翻译质量人工校对
- 其他语言版本（仅中→英）
