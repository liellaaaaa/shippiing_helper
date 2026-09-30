# -*- coding: utf-8 -*-
"""
回填 audit_logs 中 user_name='unknown' 的操作人。

根因：auth_middleware 白名单 `startswith("/api/v1/msds")` 覆盖了
`/api/v1/msds-ledger`，请求未解析 JWT，审计写入 user_name='unknown'。

归属依据（本地同步副本交叉验证）：
  IP 主属（已知日志 100%/压倒性多数）+ 时间窗（±30min 同 IP 业务操作）

  192.168.50.248 -> 向嘉倩   （9 月该 IP 已知操作全部为向嘉倩；unknown 紧随其 pi_upload/ledger_write）
  192.168.50.167 -> 刘洁婷   （40/40 已知均为刘洁婷；30/30 时间窗命中）
  192.168.50.119 -> 潘慧兰   （33/33 已知均为潘慧兰；25/25 同 IP 最近邻）
  192.168.50.102 -> 李雪     （22 条已知为李雪；11/11 时间窗命中）
  192.168.50.230 -> 肖聪     （9 月该 IP 22 条已知全部为肖聪，开发机）

用法：
  python backend/migrations/022_backfill_audit_unknown_user.py            # 预览
  python backend/migrations/022_backfill_audit_unknown_user.py --apply    # 执行
"""
import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.environ.get(
    "SHIPPING_DB_PATH",
    os.path.join(ROOT, "data", "shipping_helper.db"),
)

# IP -> 操作人（见模块 docstring 证据）
IP_OWNER = {
    "192.168.50.248": "向嘉倩",
    "192.168.50.167": "刘洁婷",
    "192.168.50.119": "潘慧兰",
    "192.168.50.102": "李雪",
    "192.168.50.230": "肖聪",
}

MARK = "backfilled:ip-map"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="实际写入（默认仅预览）")
    parser.add_argument("--db", default=DB_PATH)
    args = parser.parse_args()

    if not os.path.isfile(args.db):
        print(f"DB not found: {args.db}")
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    rows = list(cur.execute(
        "SELECT id, event_type, action_time, ip_address, detail "
        "FROM audit_logs WHERE user_name='unknown' ORDER BY id"
    ))
    print(f"unknown rows: {len(rows)}")

    plan = []
    for rid, etype, atime, ip, detail in rows:
        owner = IP_OWNER.get(ip or "")
        plan.append((rid, etype, atime, ip, owner, detail))

    from collections import Counter
    counts = Counter((p[3], p[4]) for p in plan)
    print("\n预览归属（IP -> 人数）:")
    for (ip, owner), n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {ip or '(empty)'} -> {owner or '**无法归属**'} : {n}")

    unmapped = [p for p in plan if not p[4]]
    if unmapped:
        print(f"\n无法归属 {len(unmapped)} 条，保持 unknown:")
        for p in unmapped[:20]:
            print(f"  id={p[0]} {p[2]} {p[1]} ip={p[3]}")

    if not args.apply:
        print("\n[预览模式] 加 --apply 执行写入")
        conn.close()
        return

    backup = args.db + ".bak_before_user_backfill_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(args.db, backup)
    print(f"\n已备份: {backup}")

    updated = 0
    for rid, etype, atime, ip, owner, detail in plan:
        if not owner:
            continue
        new_detail = detail or ""
        note = f"[{MARK} owner={owner} ip={ip}]"
        if note not in new_detail:
            new_detail = (new_detail + " " + note).strip()
        cur.execute(
            "UPDATE audit_logs SET user_name=?, detail=? WHERE id=? AND user_name='unknown'",
            (owner, new_detail, rid),
        )
        updated += cur.rowcount

    conn.commit()
    print(f"updated: {updated}")

    print("\n回填后 user_name 分布:")
    for r in cur.execute(
        "SELECT user_name, COUNT(*) FROM audit_logs GROUP BY user_name ORDER BY 2 DESC"
    ):
        print(f"  {r[0]}: {r[1]}")

    remaining = list(cur.execute(
        "SELECT id, ip_address FROM audit_logs WHERE user_name='unknown'"
    ))
    print(f"仍为 unknown: {len(remaining)}")
    conn.close()


if __name__ == "__main__":
    main()
