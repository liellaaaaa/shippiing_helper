# 包装计算彻底整改实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 包装计算与船务规格/清关成品一致（件数/托数/毛重/体积/清关口径）

**Architecture:** 单一公式 `packages=ceil(qty/fill)`、`pallets=ceil(packages/cap)`、`gross=net+packages*tare+pallets*pal_wt`、`volume=packages*cbm+pallets*pal_cbm`；数据层校准卡板与包装；前端禁止按板位算体积毛重；清关件数默认打件数。

**Tech Stack:** FastAPI + SQLAlchemy + SQLite + Vue3 + Element Plus

**设计文档:** `docs/superpowers/specs/2026-09-24-packaging-calc-overhaul.md`

---

### Task 1: Migration 校准 pallets + packaging_types

**Files:**
- Create: `backend/migrations/019_fix_packaging_pallet_specs.py`

- [ ] 写入卡板 16/0.15、19/0.1815
- [ ] 覆盖 packaging_types 12 行（名称对齐 200kg双环闭口桶、1吨桶）
- [ ] 执行 migration 并用 sqlite 验证

### Task 2: packaging_service 单一公式

**Files:**
- Modify: `backend/app/services/packaging_service.py`
- Modify: `backend/app/services/calculation_service.py`
- Test: `backend/tests/test_packaging_calc_overhaul.py`

- [ ] 黄金用例 G1–G6 写成失败测试
- [ ] 改 `calculate` / `calculate_single_product` / `calculate_order_packaging` / `calculate_remainder_contribution`
- [ ] 测试通过

### Task 3: PackagingCalculator 前端

**Files:**
- Modify: `frontend/src/components/phase1/PackagingCalculator.vue`

- [ ] `onPalletsChange` 改为按件数
- [ ] 托数 `ceil`；件数只读；体积可实测覆盖
- [ ] 合板开关；去掉余数双计

### Task 4: 清关口径

**Files:**
- Modify: `backend/app/services/clearance_fields.py`

- [ ] package 默认 drums
- [ ] totals 句对齐成品
- [ ] COA QUANTITY = net（已由 payload 提供）

### Task 5: 回归

- [ ] `pytest backend/tests -q`
- [ ] 黄金用例全绿
