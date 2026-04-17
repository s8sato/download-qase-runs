#!/usr/bin/env python3
"""Download Qase test run reports as PDF and/or CSV."""

import argparse
import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright, BrowserContext, Page

AUTH_STATE = Path.home() / ".config" / "download-qase-runs" / "auth_state.json"
BASE = "https://app.qase.io"


def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download Qase run reports (PDF/CSV).")
    p.add_argument("project", help="Qase project key, e.g. SANDBOX")
    p.add_argument(
        "--dir",
        metavar="DIR",
        help="Output directory (default: ./qase/runs/<PROJECT>/)",
    )
    p.add_argument("--pdf", action="store_true", help="Export PDF reports")
    p.add_argument("--csv", action="store_true", help="Export CSV reports")
    args = p.parse_args()
    if not args.pdf and not args.csv:
        p.error("At least one of --pdf, --csv must be specified.")
    return args


async def authenticate(playwright):
    """Return (browser, context, page), logging in interactively if necessary."""
    browser = await playwright.chromium.launch(headless=False)
    kwargs = {"storage_state": str(AUTH_STATE)} if AUTH_STATE.exists() else {}
    context = await browser.new_context(**kwargs)
    page = await context.new_page()
    page.set_default_navigation_timeout(60_000)

    await page.goto(f"{BASE}/projects", wait_until="domcontentloaded")

    if "/login" in page.url:
        print("Please log in to Qase in the browser window.")
        await page.wait_for_url(lambda url: "/login" not in url, timeout=180_000)
        print("Logged in.")
        AUTH_STATE.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(AUTH_STATE))

    return browser, context, page


async def _collect_ids_from_page_async(page: Page, project: str, ids: list[int]) -> None:
    for a in await page.locator(f"a[href*='/run/{project}/dashboard/']").all():
        href = await a.get_attribute("href") or ""
        m = re.search(r"/dashboard/(\d+)", href)
        if m:
            rid = int(m.group(1))
            if rid not in ids:
                ids.append(rid)


async def collect_run_ids(page: Page, project: str) -> list[int]:
    """Return all run IDs across all pages for the project.

    Pagination notes:
    - Page 1 is at the base URL (without ?page=1, which returns 404 if only 1 page).
    - ?page=N beyond the last page may redirect to the last page OR abort.
    - Stop when the resolved URL has already been seen, or on navigation error.
    """
    runs_url = f"{BASE}/run/{project}"
    ids: list[int] = []
    seen: set[str] = set()

    # Selector that appears only after the run list has rendered.
    # We do NOT use generic tags like h1/button/table which appear in the nav
    # before the content is ready.
    RUN_LINK_SEL = f"a[href*='/run/{project}/dashboard/']"

    async def wait_for_runs_or_empty():
        """Wait for run links, or give up after 20 s (empty/no-runs page)."""
        try:
            await page.wait_for_selector(RUN_LINK_SEL, timeout=20_000)
        except Exception:
            pass  # No runs on this page — that's fine.

    page.set_default_navigation_timeout(60_000)
    await page.goto(runs_url, wait_until="domcontentloaded")
    await wait_for_runs_or_empty()

    pg = 1
    while True:
        cur = page.url
        if cur in seen:
            break
        seen.add(cur)

        await _collect_ids_from_page_async(page, project, ids)

        pg += 1
        try:
            await page.goto(f"{runs_url}?page={pg}", wait_until="domcontentloaded")
            await wait_for_runs_or_empty()
        except Exception:
            # Navigation aborted or failed — we've gone past the last page.
            break
        # If redirected back to a URL already seen, we've exceeded the last page.
        if page.url in seen:
            break

    return ids


async def do_export(page: Page, fmt: str, dest: Path) -> bool:
    """Click the page-level Export button, set the format in the dialog, download."""

    # ── 1. Click the page-level "Export" button (not inside any dialog) ──
    trigger = page.locator("button:has-text('Export')").first
    if not await trigger.count():
        print("    ✗ export trigger not found", file=sys.stderr)
        return False
    await trigger.click()

    # ── 2. Wait for the export dialog to appear ───────────────────────────
    dialog = page.locator("dialog")
    try:
        await dialog.wait_for(state="visible", timeout=10_000)
    except Exception:
        print("    ✗ export dialog did not appear", file=sys.stderr)
        return False

    # ── 3. If PDF is needed, change the format combobox ──────────────────
    if fmt.upper() == "PDF":
        combobox = dialog.locator("[role='combobox']")
        await combobox.click()
        # Wait for the listbox to open
        listbox = page.locator("[role='listbox']")
        try:
            await listbox.wait_for(state="visible", timeout=5_000)
        except Exception:
            print("    ✗ format listbox did not open", file=sys.stderr)
            await page.keyboard.press("Escape")
            return False
        pdf_option = listbox.locator("[role='option']:has-text('PDF')")
        try:
            await pdf_option.wait_for(state="visible", timeout=5_000)
            await pdf_option.click()
        except Exception:
            print("    ✗ PDF option not found in listbox", file=sys.stderr)
            await page.keyboard.press("Escape")
            return False
    # CSV is the default — no change needed.

    # ── 4. Click the "Export" button inside the dialog to download ────────
    export_in_dialog = dialog.locator("button:has-text('Export')")
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with page.expect_download(timeout=60_000) as dl_info:
        await export_in_dialog.click()
    dl = await dl_info.value
    await dl.save_as(str(dest))
    return True


async def process_run(
    ctx: BrowserContext,
    project: str,
    run_id: int,
    out: Path,
    pdf: bool,
    csv: bool,
) -> None:
    page = await ctx.new_page()
    page.set_default_navigation_timeout(60_000)
    await page.goto(
        f"{BASE}/run/{project}/dashboard/{run_id}", wait_until="domcontentloaded"
    )
    # Wait until the dashboard Export button is present.
    await page.wait_for_selector("button:has-text('Export')", timeout=30_000)

    if pdf:
        dest = out / "pdf" / f"{run_id}.pdf"
        if dest.exists():
            print(f"  skip {dest}")
        else:
            ok = await do_export(page, "PDF", dest)
            print(f"  {'✓' if ok else '✗'} {dest}")

    if csv:
        dest = out / "csv" / f"{run_id}.csv"
        if dest.exists():
            print(f"  skip {dest}")
        else:
            if pdf:
                # Reload to reset UI state before second export
                await page.reload(wait_until="domcontentloaded")
                await page.wait_for_selector("button:has-text('Export')", timeout=30_000)
            ok = await do_export(page, "CSV", dest)
            print(f"  {'✓' if ok else '✗'} {dest}")

    await page.close()


async def run(args: argparse.Namespace) -> None:
    out = Path(args.dir) if args.dir else Path("qase") / args.project / "runs"

    async with async_playwright() as pw:
        browser, ctx, page = await authenticate(pw)

        print(f"Collecting runs for project '{args.project}' …")
        ids = await collect_run_ids(page, args.project)
        print(f"Found {len(ids)} run(s).")

        for rid in ids:
            print(f"Run {rid}:")
            await process_run(ctx, args.project, rid, out, args.pdf, args.csv)

        await browser.close()

    print("Done.")


def main() -> None:
    asyncio.run(run(cli()))


if __name__ == "__main__":
    main()
