# 报关资料字段优化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现报关资料生成中贸易国/运抵国/指运港的分离、中文化、以及所有产品申报要素的完整填充

**Architecture:** 单文件改动（`document_service.py`），新增 `parse_destination()` 函数和两个翻译字典，修改 `generate_customs()` 中的字段填充逻辑

**Tech Stack:** Python + openpyxl

---

### Task 1: 新增翻译字典和 parse_destination() 函数

**Files:**
- Modify: `backend/app/services/document_service.py`（替换旧的 `cn_port()` 函数，新增两个翻译字典和 `parse_destination()`）

- [ ] **Step 1: 删除旧的 `cn_port()` 函数，替换为翻译字典 + `parse_destination()`**

  找到 `generate_customs()` 方法内部的 `cn_port()` 函数（第651-684行），将其替换为文件级别的两个翻译字典和 `parse_destination()` 函数。

  在文件顶部、`class DocumentService:` 声明之前，添加：

  ```python
  # 国家名英文→中文翻译表
  COUNTRY_CN_MAP: dict[str, str] = {
      "turkey": "土耳其", "turkiye": "土耳其",
      "china": "中国",
      "india": "印度",
      "indonesia": "印度尼西亚",
      "thailand": "泰国",
      "singapore": "新加坡",
      "malaysia": "马来西亚",
      "vietnam": "越南",
      "bangladesh": "孟加拉国",
      "philippines": "菲律宾",
      "korea": "韩国",
      "japan": "日本",
      "taiwan": "台湾",
      "usa": "美国", "united states": "美国",
      "uk": "英国", "united kingdom": "英国",
      "germany": "德国",
      "france": "法国",
      "netherlands": "荷兰",
      "italy": "意大利",
      "spain": "西班牙",
      "australia": "澳大利亚",
      "russia": "俄罗斯",
      "brazil": "巴西",
      "mexico": "墨西哥",
      "canada": "加拿大",
      "egypt": "埃及",
      "south africa": "南非",
      "nigeria": "尼日利亚",
      "kenya": "肯尼亚",
      "pakistan": "巴基斯坦",
      "sri lanka": "斯里兰卡",
      "myanmar": "缅甸",
      "cambodia": "柬埔寨",
      "laos": "老挝",
      "nepal": "尼泊尔",
      "argentina": "阿根廷",
      "chile": "智利",
      "colombia": "哥伦比亚",
      "peru": "秘鲁",
      "ecuador": "厄瓜多尔",
      "saudi arabia": "沙特阿拉伯",
      "uae": "阿联酋", "united arab emirates": "阿联酋",
      "iran": "伊朗",
      "israel": "以色列",
      "poland": "波兰",
      "ukraine": "乌克兰",
      "belgium": "比利时",
      "switzerland": "瑞士",
      "sweden": "瑞典",
      "norway": "挪威",
      "denmark": "丹麦",
      "portugal": "葡萄牙",
      "greece": "希腊",
      "new zealand": "新西兰",
  }

  # 城市/港口名英文→中文翻译表
  CITY_CN_MAP: dict[str, str] = {
      "izmit": "伊兹米特", "kocaeli": "科贾埃利",
      "istanbul": "伊斯坦布尔",
      "mersin": "梅尔辛",
      "aliaga": "阿利亚加",
      "ambarlı": "安巴利",
      "jakarta": "雅加达",
      "surabaya": "泗水",
      "tanjung priok": "丹戎不碌",
      "bangkok": "曼谷", "tangkok": "曼谷",
      "laem chabang": "林查班",
      "lat krabang": "拉格拉邦",
      "ho chi minh": "胡志明市", "hcmc": "胡志明市",
      "haiphong": "海防",
      "manila": "马尼拉",
      "busan": "釜山",
      "incheon": "仁川",
      "tokyo": "东京",
      "yokohama": "横滨",
      "osaka": "大阪",
      "shanghai": "上海",
      "ningbo": "宁波",
      "qingdao": "青岛",
      "tianjin": "天津",
      "dalian": "大连",
      "xiamen": "厦门",
      "guangzhou": "广州",
      "shenzhen": "深圳",
      "yantian": "盐田",
      "shekou": "蛇口",
      "chiwan": "赤湾",
      "hong kong": "香港", "hkg": "香港",
      "taipei": "台北",
      "kaohsiung": "高雄",
      "singapore port": "新加坡",
      "port of singapore": "新加坡",
      "colombo": "科伦坡",
      "chennai": "金奈",
      "mumbai": "孟买",
      "nhava sheva": "尼赫鲁港",
      "karachi": "卡拉奇",
      "chittagong": "吉大港",
      "port klang": "巴生港",
      "penang": "槟城",
      "dubai": "迪拜",
      "jebel ali": "杰贝阿里",
      "rikushentity": "六横",
      "los angeles": "洛杉矶",
      "long beach": "长滩",
      "new york": "纽约",
      "rotterdam": "鹿特丹",
      "hamburg": "汉堡",
      "antwerp": "安特卫普",
      "gdansk": "格但斯克",
      "london": "伦敦",
      "felixstowe": "费利克斯托",
      "le havre": "勒阿弗尔",
      "barcelona": "巴塞罗那",
      "valencia": "瓦伦西亚",
      "genoa": "热那亚",
      "auckland": "奥克兰",
      "sydney": "悉尼",
      "melbourne": "墨尔本",
      "durresi": "都拉斯",
      "abidjan": "阿比让",
      "mombasa": "蒙巴萨",
      "lagos": "拉各斯",
      "dakar": "达喀尔",
      "casablanca": "卡萨布兰卡",
      "alexandria": "亚历山大",
      "port said": "塞得港",
      "damietta": "达米埃塔",
  }


  def _lookup_city(dest_lower: str) -> str | None:
      """尝试匹配城市名的中文翻译"""
      if dest_lower in CITY_CN_MAP:
          return CITY_CN_MAP[dest_lower]
      for key, val in CITY_CN_MAP.items():
          if key in dest_lower or dest_lower in key:
              return val
      return None


  def _lookup_country(dest_lower: str) -> str | None:
      """尝试匹配国家名的中文翻译"""
      if dest_lower in COUNTRY_CN_MAP:
          return COUNTRY_CN_MAP[dest_lower]
      for key, val in COUNTRY_CN_MAP.items():
          if key in dest_lower or dest_lower in key:
              return val
      return None


  def parse_destination(dest: str) -> tuple[str, str]:
      """
      将目的港字段（如 "Izmit,Turkiye"）解析为 (指运港中文, 国家中文)。
      策略：
      1. 按逗号分割，分别匹配城市和国家翻译
      2. 无逗号时尝试整个字符串匹配国家表或城市表
      3. 都匹配不到返回原值
      """
      if not dest:
          return ("", "")

      dest_stripped = dest.strip()

      # 策略1：按逗号分割
      if "," in dest_stripped:
          parts = [p.strip() for p in dest_stripped.split(",", 1)]
          city_part = parts[0]
          country_part = parts[1] if len(parts) > 1 else ""

          city_cn = _lookup_city(city_part.lower())
          country_cn = _lookup_country(country_part.lower())

          # 如果逗号前匹配到国家（如 "Turkey, City" 的反向情况），交换
          if not city_cn and not country_cn:
              # 都匹配不到：尝试反向
              city_cn = _lookup_city(country_part.lower())
              country_cn = _lookup_country(city_part.lower())

          # 部分匹配成功时填充缺失方
          if not city_cn:
              # 城市没匹配到，用原城市名英文
              city_cn = city_part
          if not country_cn:
              # 国家没匹配到，用原国家名英文
              country_cn = country_part

          return (city_cn, country_cn)

      # 策略2：无逗号，尝试整体匹配国家表
      country_cn = _lookup_country(dest_stripped.lower())
      if country_cn:
          return (dest_stripped, country_cn)

      # 策略3：无逗号，尝试整体匹配城市表
      city_cn = _lookup_city(dest_stripped.lower())
      if city_cn:
          return (city_cn, dest_stripped)

      # 都匹配不到，返回原值
      return (dest_stripped, dest_stripped)
  ```

- [ ] **Step 2: 验证新增代码语法正确**

  Run: `python -c "import ast; ast.parse(open('backend/app/services/document_service.py').read()); print('OK')"`
  Expected: OK

- [ ] **Step 3: 提交**

  ```bash
  git add backend/app/services/document_service.py
  git commit -m "feat: add country/city translation dicts and parse_destination()"
  ```

---

### Task 2: 更新 generate_customs() 的字段填充逻辑

**Files:**
- Modify: `backend/app/services/document_service.py`

- [ ] **Step 1: 修改表头字段填充**

  在 `generate_customs()` 中找到原来使用 `cn_port()` 和 `dest_raw` 的代码（第705-730行）：

  ```python
  # ── 基本信息（从台账提取）──────────────────────────────────
  pi_no = record.order_no or ""
  consignee = record.consignee_name or ""
  consignee_addr = record.consignee_address or ""
  dest_raw = record.destination or ""
  dest_cn = cn_port(dest_raw)
  dest_port = dest_raw
  ```

  改为：

  ```python
  # ── 基本信息（从台账提取）──────────────────────────────────
  pi_no = record.order_no or ""
  consignee = record.consignee_name or ""
  consignee_addr = record.consignee_address or ""
  dest_raw = record.destination or ""
  dest_city_cn, dest_country_cn = parse_destination(dest_raw)
  ```

- [ ] **Step 2: 修改表头占位符替换**

  将原来使用 `dest_cn` 和 `dest_port` 的占位符替换（第728-730行）：

  ```python
  replace_placeholder(ws, "{{DEST_COUNTRY_CN}}", dest_cn)
  replace_placeholder(ws, "{{DEST_COUNTRY_CN_2}}", dest_cn)
  replace_placeholder(ws, "{{DEST_PORT}}", dest_port)
  ```

  改为：

  ```python
  replace_placeholder(ws, "{{DEST_COUNTRY_CN}}", dest_country_cn)
  replace_placeholder(ws, "{{DEST_COUNTRY_CN_2}}", dest_country_cn)
  replace_placeholder(ws, "{{DEST_PORT}}", dest_city_cn)
  ```

- [ ] **Step 3: 修改最终目的国填充**

  在 item 循环中找到最终目的国填充（第771-772行）：

  ```python
  if dest_cn:
      ws.cell(row, 13, dest_cn)                      # M: 最终目的国
  ```

  改为：

  ```python
  if dest_country_cn:
      ws.cell(row, 13, dest_country_cn)               # M: 最终目的国
  ```

- [ ] **Step 4: 修改箱单和合同 sheet 中的 dest_raw 引用**

  找到箱单 sheet 中 C7 的填充（第890-891行）：

  ```python
  if dest_raw:
      ws.cell(7, 3).value = f"广州  至  {dest_raw}"    # C7: 船名+目的地
  ```

  这个显示的是"广州 至 Izmit,Turkiye"格式，保留原始 `dest_raw` 不变，因为这是给船公司看的描述性文字，不需要翻译。

  找到合同 sheet 中 B39 的填充（第937行）：

  ```python
  if dest_raw:
      ws["B39"] = f"(9)装运口岸和目的地           广州---{dest_raw}"
  ```

  同样保留 `dest_raw` 不变，这是装运描述。

- [ ] **Step 5: 修改合同 sheet 中的 DEST_PORT 占位符**

  找到合同 sheet 中 DEST_PORT 占位符（第930行）：

  ```python
  replace_placeholder(ws, "{{DEST_PORT}}", dest_port)
  ```

  改为：

  ```python
  replace_placeholder(ws, "{{DEST_PORT}}", dest_city_cn)
  ```

  此外，检查 `dest_cn` 是否还有其它引用（全文搜索 `dest_cn` 确保全部替换）。

- [ ] **Step 6: 提交**

  ```bash
  git add backend/app/services/document_service.py
  git commit -m "feat: update generate_customs() to use parsed destination fields"
  ```

---

### Task 3: 所有产品填充 row+2（币制/数量引用）

**Files:**
- Modify: `backend/app/services/document_service.py`

- [ ] **Step 1: 在 item 循环中添加 row+2 填充**

  在 `generate_customs()` 的 item 循环中找到声明要素和总价的填充（第798-804行），在其后面添加 row+2 的填充：

  找到这段代码：
  ```python
              if decl_str:
                  ws.cell(row + 1, 4, decl_str)                  # D21: 申报要素

              # 总价（行 row+1, I 列）— 模板公式 =I20*G20 会自动计算，
              # 但 openpyxl 保存后公式缓存值可能不更新，所以直接写值
              if item.total_amount:
                  ws.cell(row + 1, 9, item.total_amount)         # I21: 总价
   ```

  改为：

  ```python
              if decl_str:
                  ws.cell(row + 1, 4, decl_str)                  # D: 申报要素

              # 总价（行 row+1, I 列）— 模板公式 =I20*G20 会自动计算，
              # 但 openpyxl 保存后公式缓存值可能不更新，所以直接写值
              if item.total_amount:
                  ws.cell(row + 1, 9, item.total_amount)         # I: 总价

              # 币制行（行 row+2）— 数量引用 + 单位 + 币制
              ws.cell(row + 2, 7, item.quantity_kg)              # G: 数量引用
              ws.cell(row + 2, 8, "千克")                         # H: 单位
              ws.cell(row + 2, 9, currency)                      # I: 币制
  ```

- [ ] **Step 2: 提交**

  ```bash
  git add backend/app/services/document_service.py
  git commit -m "feat: fill currency/quantity row for all items in customs declaration"
  ```

---

### Task 4: 移除旧的 cn_port() 函数（清理）

**Files:**
- Modify: `backend/app/services/document_service.py`

- [ ] **Step 1: 删除 `cn_port()` 函数**

  确认 `generate_customs()` 方法内已无任何代码引用 `cn_port`，然后在方法体中删除 `def cn_port(dest):` 整个函数定义（原第651-684行）。

- [ ] **Step 2: 验证改后代码语法正确**

  Run: `python -c "import ast; ast.parse(open('backend/app/services/document_service.py').read()); print('OK')"`
  Expected: OK

- [ ] **Step 3: 提交**

  ```bash
  git add backend/app/services/document_service.py
  git commit -m "refactor: remove obsolete cn_port() function"
  ```

---

### Task 5: 验证

- [ ] **Step 1: 验证后端能正常启动**

  Run: 从 `backend/` 目录启动 `uvicorn app.main:app --reload`
  Expected: 启动无报错

- [ ] **Step 2: 生成报关资料确认字段正确**

  在浏览器中进入 Phase 2 工作流，选择一个台账记录，生成报关资料，用 OnlyOffice 打开验证：
  - E10（贸易国）和 G10（运抵国）显示中文国家名
  - K10（指运港）显示中文城市名
  - M列（最终目的国）每行显示中文国家名
  - 每个产品的 I22/I25/I28/... 行均显示币制
  - 每个产品的 G22/G25/G28/... 行均显示数量引用

- [ ] **Step 3: 提交**

  ```bash
  git add backend/app/services/document_service.py
  git commit -m "verification: customs declaration fields confirmed working"
  ```
