# Data Center Directory Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the keyword-search-only data center with a directory tree browser that displays the full `references/` folder structure using el-tree, retaining search filtering and file preview.

**Architecture:** Backend exposes a new `GET /api/v1/data-center/tree` endpoint that recursively scans `references/` and returns a nested JSON tree. Frontend uses Element Plus `el-tree` with `show-icon` and custom file-type icons. File clicks trigger preview in the right panel.

**Tech Stack:** Python/FastAPI backend, Vue 3 + Element Plus el-tree frontend, no new dependencies.

---

## File Structure

```
backend/
├── app/
│   ├── api/v1/data_center.py          # MODIFY: add /tree endpoint
│   └── services/data_center_service.py # MODIFY: add get_directory_tree()
frontend/
└── src/
    ├── api/phase2.ts                  # MODIFY: add getDataCenterTree()
    └── views/data-center/
        └── DataCenter.vue             # MODIFY: replace list with el-tree
```

---

## Task 1: Backend — Add `get_directory_tree()` to DataCenterService

**Files:**
- Modify: `backend/app/services/data_center_service.py`

- [ ] **Step 1: Add `get_directory_tree()` method**

Add the following method to `DataCenterService` class in `data_center_service.py`:

```python
def get_directory_tree(self, root_dir: str) -> list[dict]:
    """
    Recursively scan root_dir and return a nested tree structure.
    Each node: { label, key, isLeaf, file_type, file_path, children: [] }
    file_type: 'folder' | 'pdf' | 'doc' | 'docx' | 'xls' | 'xlsx' | 'json' | 'other'
    Only folders with at least one file are included.
    """
    def scan_dir(dir_path: str) -> list[dict]:
        nodes = []
        try:
            for entry in sorted(os.scandir(dir_path), key=lambda e: e.name):
                if entry.is_dir():
                    children = scan_dir(entry.path)
                    # Only include folder if it has children
                    if children:
                        nodes.append({
                            "label": entry.name,
                            "key": entry.path,
                            "isLeaf": False,
                            "file_type": "folder",
                            "children": children,
                        })
                elif entry.is_file():
                    ext = os.path.splitext(entry.name)[1].lower()
                    file_type_map = {
                        ".pdf": "pdf",
                        ".doc": "doc",
                        ".docx": "docx",
                        ".xls": "xls",
                        ".xlsx": "xlsx",
                        ".json": "json",
                    }
                    file_type = file_type_map.get(ext, "other")
                    nodes.append({
                        "label": entry.name,
                        "key": entry.path,
                        "isLeaf": True,
                        "file_type": file_type,
                        "file_path": entry.path,
                    })
        except PermissionError:
            pass
        return nodes

    return scan_dir(root_dir)
```

- [ ] **Step 2: Test the method**

Run in backend shell:
```python
from app.services.data_center_service import DataCenterService
svc = DataCenterService()
tree = svc.get_directory_tree("references/")
print(len(tree), "top-level nodes")
print(tree[0])  # should show first node structure
```

Expected: Prints tree with at least 3 top-level nodes (MSDS, 海运鉴定报告, and root files like packaging_data.json).

---

## Task 2: Backend — Add `GET /api/v1/data-center/tree` Endpoint

**Files:**
- Modify: `backend/app/api/v1/data_center.py`
- Modify: `backend/app/core/config.py` (if needed)

- [ ] **Step 1: Check REFERENCES_DIR in config**

Check `backend/app/core/config.py` for the `REFERENCES_DIR` constant. It should point to the project root `references/` folder. If it doesn't exist, add:
```python
REFERENCES_DIR = os.getenv("REFERENCES_DIR", str(Path(__file__).parent.parent.parent.parent / "references"))
```

- [ ] **Step 2: Add `/tree` endpoint**

Add to `data_center.py`:

```python
from app.core.config import REFERENCES_DIR

@router.get("/tree")
async def get_data_center_tree():
    """Return the full references/ directory as a nested tree."""
    svc = DataCenterService()
    tree = svc.get_directory_tree(REFERENCES_DIR)
    return {"tree": tree, "total": sum(1 for node in tree if node.get("isLeaf"))}
```

- [ ] **Step 3: Verify endpoint**

Run: `curl http://localhost:8000/api/v1/data-center/tree`
Expected: JSON with `{"tree": [...], "total": N}` where tree is the full directory structure.

---

## Task 3: Frontend — Add `getDataCenterTree()` API

**Files:**
- Modify: `frontend/src/api/phase2.ts`

- [ ] **Step 1: Add `getDataCenterTree()` method**

Add to `phase2Api` object in `phase2.ts`:

```typescript
getDataCenterTree() {
  return axios.get('/api/v1/data-center/tree')
},
```

---

## Task 4: Frontend — Rewrite DataCenter.vue with el-tree

**Files:**
- Modify: `frontend/src/views/data-center/DataCenter.vue`

- [ ] **Step 1: Define tree data structure**

Add at top of `<script setup>`:

```typescript
interface TreeNode {
  label: string
  key: string
  isLeaf: boolean
  file_type: string
  file_path?: string
  children?: TreeNode[]
}

const msdsTree = ref<TreeNode[]>([])
const transportTree = ref<TreeNode[]>([])
const selectedFile = ref<TreeNode | null>(null)
```

- [ ] **Step 2: Load tree data on mount and tab switch**

Add `loadTree()` function:

```typescript
async function loadTree() {
  try {
    const res = await phase2Api.getDataCenterTree()
    const tree = res.data.tree as TreeNode[]
    // Split into MSDS and transport trees
    const msdsNode = tree.find(n => n.label === 'MSDS')
    const transportNode = tree.find(n => n.label === '海运鉴定报告')
    msdsTree.value = msdsNode?.children || []
    transportTree.value = transportNode?.children || []
  } catch (e) {
    ElMessage.error('加载目录树失败')
  }
}
```

Call `loadTree()` in `onMounted` and when `activeTab` changes.

- [ ] **Step 3: Add el-tree template**

Replace the search results list section with:

```html
<!-- MSDS Tree -->
<div v-if="activeTab === 'msds'" class="file-tree-wrapper">
  <el-tree
    :data="msdsTree"
    :props="{ children: 'children', label: 'label', isLeaf: 'isLeaf' }"
    node-key="key"
    :filter-node-method="filterNode"
    default-expand-all
    @node-click="onFileClick"
    class="file-tree"
  >
    <template #default="{ node, data }">
      <span class="tree-node">
        <span class="node-icon">{{ getFileIcon(data) }}</span>
        <span class="node-label">{{ node.label }}</span>
      </span>
    </template>
  </el-tree>
</div>

<!-- Transport Tree -->
<div v-else class="file-tree-wrapper">
  <el-tree
    :data="transportTree"
    :props="{ children: 'children', label: 'label', isLeaf: 'isLeaf' }"
    node-key="key"
    :filter-node-method="filterNode"
    default-expand-all
    @node-click="onFileClick"
    class="file-tree"
  >
    <template #default="{ node, data }">
      <span class="tree-node">
        <span class="node-icon">{{ getFileIcon(data) }}</span>
        <span class="node-label">{{ node.label }}</span>
      </span>
    </template>
  </el-tree>
</div>
```

- [ ] **Step 4: Add helper functions**

```typescript
function getFileIcon(data: TreeNode): string {
  const icons: Record<string, string> = {
    folder: '📁',
    pdf: '📄',
    doc: '📝',
    docx: '📝',
    xls: '📊',
    xlsx: '📊',
    json: '⚙️',
    other: '📎',
  }
  return icons[data.file_type] || '📎'
}

function onFileClick(data: TreeNode) {
  if (!data.isLeaf) return
  selectedFile.value = data
  previewFilename.value = data.label
}

function filterNode(query: string, data: TreeNode): boolean {
  return data.label.toLowerCase().includes(query.toLowerCase())
}
```

- [ ] **Step 5: Add tree styles**

```css
.file-tree-wrapper {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  overflow: hidden;
  max-height: 400px;
  overflow-y: auto;
}
.file-tree {
  background: transparent;
}
.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.node-icon { font-size: 14px; }
.node-label {
  font-family: 'JetBrains Mono', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

---

## Task 5: Test End-to-End

- [ ] **Step 1: Start backend**

```bash
cd backend && uvicorn app.main:app --reload
```

- [ ] **Step 2: Start frontend**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Verify tree loads**

Navigate to Data Center page. Confirm:
- MSDS tab shows directory tree with files
- Transport tab shows transport reports tree
- Clicking a file shows preview on right

- [ ] **Step 4: Verify search filtering**

Type in search box. Confirm el-tree filters the visible nodes.

---

## Task 6: Commit

```bash
git add backend/app/api/v1/data_center.py backend/app/services/data_center_service.py frontend/src/api/phase2.ts frontend/src/views/data-center/DataCenter.vue
git commit -m "feat(data-center): add directory tree browser for references/"
git push
```