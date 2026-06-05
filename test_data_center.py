#!/usr/bin/env python3
"""Test DataCenterPanel feature via Playwright."""
from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:5173"

def test_data_center():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("response", lambda r: errors.append(f"{r.status} {r.url}") if r.status >= 400 else None)

        # Navigate to Phase 2
        page.goto(f"{FRONTEND}/phase2", timeout=15000)
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)
        print("=== Phase 2 Page Loaded ===")

        # Find "数据中心" tab in ReferencePanel
        tabs = page.locator(".el-collapse-item__header").all()
        tab_names = [t.inner_text().strip() for t in tabs]
        print(f"ReferencePanel tabs: {tab_names}")

        dc_tab = None
        for t in tabs:
            if "数据中心" in t.inner_text():
                dc_tab = t
                break

        if dc_tab is None:
            print("FAIL: '数据中心' tab not found")
            browser.close()
            return

        print("PASS: '数据中心' tab found")
        dc_tab.click()
        page.wait_for_timeout(1000)

        # Look for search input in the data center section
        search_inputs = page.locator(".el-input__inner, input[class*='search'], input[placeholder]").all()
        search_input = None
        for inp in search_inputs:
            placeholder = inp.get_attribute("placeholder") or ""
            if "搜索" in placeholder or "FIXING" in placeholder or "search" in placeholder.lower():
                search_input = inp
                break

        if search_input is None:
            # Try finding by type
            all_inputs = page.locator("input").all()
            for inp in all_inputs:
                ph = inp.get_attribute("placeholder") or ""
                print(f"  Input: {ph[:50]}")
            search_input = all_inputs[0] if all_inputs else None

        if search_input:
            print(f"Found search input, typing '柔软剂'...")
            search_input.fill("柔软剂")
            page.wait_for_timeout(1500)
            # Check results
            result_items = page.locator(".el-select-dropdown__item, .el-table__row, [class*='item']").all()
            print(f"  Result items: {len(result_items)}")
        else:
            print("Search input not found, checking UI structure...")
            # Take screenshot of the data center area
            panel = page.locator(".el-collapse-item__content").last
            if panel.count() > 0:
                print(f"  DataCenter panel content visible: {panel.is_visible()}")

        print()
        if errors:
            print(f"Console errors ({len(errors)}):")
            for e in errors[:5]:
                print(f"  {e[:150]}")
        else:
            print("No console errors")

        browser.close()
        print("\nTest complete.")


if __name__ == "__main__":
    test_data_center()
