"""Push the resolved references into a running Zotero via its connector API.

Reads references/resolution_report.json (written by resolve_references.py),
fetches full metadata from Crossref for each verified DOI, and saves the items
into a chosen collection. Each item carries a note explaining which part of the
pipeline depends on it, plus tags for filtering.

    python scripts/import_to_zotero.py --list-collections
    python scripts/import_to_zotero.py --target C13 --dry-run
    python scripts/import_to_zotero.py --target C13

Zotero only accepts attachments for items created in the same save session, so
PDFs cannot be added to items imported by an earlier run. For those, select them
in Zotero and use 'Find Available PDFs' instead.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

CONNECTOR = "http://localhost:23119/connector"
MAILTO = "solar-burst-multiview@fhnw.ch"
REPORT = Path(__file__).resolve().parent.parent / "references" / "resolution_report.json"
SHARED_TAG = "sharma2022-repro"

# Papers predating arXiv, served as scans by ADS. Every URL below was checked to
# return a real PDF; anything unverified is dropped rather than attached blind.
ADS_SCANS = {
    "newkirk1961": "1961ApJ...133..983N",
    "kulkarni1989": "1989AJ.....98.1112K",
    "hudson1991": "1991SoPh..133..357H",
    "parker1988": "1988ApJ...330..474P",
}


def post(endpoint: str, payload: dict) -> tuple[int, str]:
    req = urllib.request.Request(
        f"{CONNECTOR}/{endpoint}",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            # Zotero rejects connector requests without a recognised origin.
            "X-Zotero-Connector-API-Version": "3",
            "User-Agent": "solar-burst-multiview",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as fh:
            return fh.status, fh.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def post_attachment(session: str, parent_key: str, url: str, blob: bytes) -> tuple[int, str]:
    """Upload PDF bytes against a live save session.

    Zotero ignores attachment URLs handed to saveItems, because a browser
    connector holds the cookies needed to fetch them. The bytes must be pushed
    separately, and only while the session that created the parent is still open.
    """
    metadata = {
        "sessionID": session,
        "parentItemID": parent_key,
        "title": "Full Text PDF",
        "url": url,
        "contentType": "application/pdf",
    }
    req = urllib.request.Request(
        f"{CONNECTOR}/saveAttachment",
        data=blob,
        headers={
            "Content-Type": "application/pdf",
            "X-Metadata": json.dumps(metadata),
            "X-Zotero-Connector-API-Version": "3",
            "User-Agent": "solar-burst-multiview",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as fh:
            return fh.status, fh.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def download(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=180) as fh:
            blob = fh.read()
        return blob if blob[:4] == b"%PDF" else None
    except Exception:
        return None


def crossref_item(doi: str) -> dict:
    req = urllib.request.Request(
        f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto={MAILTO}",
        headers={"User-Agent": f"solar-burst-multiview (mailto:{MAILTO})"},
    )
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.load(fh)["message"]


def serves_pdf(url: str) -> bool:
    """Confirm a URL actually returns a PDF, not a paywall or bot-check page."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=45) as fh:
            return fh.read(4) == b"%PDF"
    except Exception:
        return False


def pdf_url(record: dict) -> str | None:
    """Best freely available PDF for a reference.

    arXiv is preferred over the publisher even when both are open: IOP and
    Cambridge frequently serve a bot-check page to non-browser clients, which
    Zotero would happily store as a corrupt attachment.
    """
    candidates: list[str] = []

    if record["key"] in ADS_SCANS:
        candidates.append(f"https://articles.adsabs.harvard.edu/pdf/{ADS_SCANS[record['key']]}")

    try:
        url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(record['doi'])}?email={MAILTO}"
        with urllib.request.urlopen(url, timeout=40) as fh:
            data = json.load(fh)
        locations = data.get("oa_locations") or []
        arxiv = [
            loc
            for loc in locations
            if "arxiv" in ((loc.get("url_for_pdf") or loc.get("url") or "").lower())
        ]
        for loc in arxiv + locations:
            link = loc.get("url_for_pdf")
            if link and link not in candidates:
                candidates.append(link)
    except Exception:
        pass

    for link in candidates:
        if serves_pdf(link):
            return link
    return None


def to_zotero(work: dict, record: dict) -> dict:
    creators = [
        {
            "firstName": a.get("given", ""),
            "lastName": a.get("family", ""),
            "creatorType": "author",
        }
        for a in work.get("author", []) or []
        if a.get("family")
    ]

    parts = (work.get("issued", {}).get("date-parts") or [[None]])[0]
    date = "-".join(str(p) for p in parts if p is not None)

    pages = work.get("page") or work.get("article-number") or ""

    attachments = []
    if record.get("pdf_url"):
        attachments.append(
            {
                "title": "Full Text PDF",
                "url": record["pdf_url"],
                "mimeType": "application/pdf",
            }
        )

    return {
        "itemType": "journalArticle",
        "title": (work.get("title") or [""])[0],
        "creators": creators,
        "date": date,
        "publicationTitle": (work.get("container-title") or [""])[0],
        "volume": work.get("volume", ""),
        "issue": work.get("issue", ""),
        "pages": pages,
        "DOI": work.get("DOI", ""),
        "ISSN": (work.get("ISSN") or [""])[0],
        "url": work.get("URL", ""),
        "libraryCatalog": "Crossref",
        "accessDate": time.strftime("%Y-%m-%d"),
        "attachments": attachments,
        "tags": [{"tag": SHARED_TAG}] + [{"tag": t} for t in record.get("tags", [])],
        "notes": [
            {
                "note": (
                    f"<p><b>Why this is here:</b> {record['role']}</p>"
                    f"<p>Cited by Sharma et al. (2022), ApJ 937, 99 &mdash; the paper being "
                    f"reproduced in the <code>solar-burst-multiview</code> pipeline.</p>"
                )
            }
        ],
    }


def list_collections() -> None:
    status, body = post("getSelectedCollection", {})
    if status != 200:
        print(f"Zotero did not respond ({status}). Is it running?", file=sys.stderr)
        raise SystemExit(1)
    data = json.loads(body)
    print(f"Library: {data.get('libraryName')} (editable={data.get('editable')})")
    print(f"Currently selected: {data.get('name')!r}\n")
    print("Available targets:")
    for t in data.get("targets", []):
        indent = "  " * t.get("level", 0)
        print(f"  {t['id']:<5} {indent}{t['name']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", help="collection id from --list-collections, e.g. C13")
    ap.add_argument("--list-collections", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="build items, print, save nothing")
    # The target paper is already in the library; re-saving it only makes a duplicate.
    ap.add_argument("--skip", nargs="*", default=["sharma2022"], help="reference keys to omit")
    ap.add_argument("--no-pdfs", action="store_true", help="metadata only, no attachments")
    args = ap.parse_args()

    if args.list_collections:
        list_collections()
        return 0

    records = [
        r
        for r in json.loads(REPORT.read_text())
        if r["status"] == "verified" and r["key"] not in args.skip
    ]
    if args.skip:
        print(f"Skipping (already in library): {', '.join(args.skip)}\n")
    if not records:
        print("No verified references. Run scripts/resolve_references.py first.", file=sys.stderr)
        return 1

    items = []
    for rec in records:
        if not args.no_pdfs:
            rec["pdf_url"] = pdf_url(rec)
        work = crossref_item(rec["doi"])
        items.append(to_zotero(work, rec))
        pdf = rec.get("pdf_url")
        marker = "pdf" if pdf else " - "
        print(f"  [{marker}] {rec['key']:<16} {items[-1]['title'][:56]}")
        time.sleep(0.2)

    with_pdf = sum(1 for i in items if i["attachments"])
    print(f"\n{with_pdf}/{len(items)} items have a verified PDF attachment")

    if args.dry_run:
        print(f"\nDry run: {len(items)} items built, nothing saved.")
        print(json.dumps(items[0], indent=2)[:900])
        return 0

    session = str(uuid.uuid4())
    status, body = post(
        "saveItems",
        {"items": items, "sessionID": session, "uri": "https://doi.org/10.3847/1538-4357/ac87fc"},
    )
    if status not in (200, 201):
        print(f"saveItems failed ({status}): {body[:400]}", file=sys.stderr)
        return 1
    print(f"\nSaved {len(items)} items to Zotero.")

    if args.target:
        status, target_body = post(
            "updateSession",
            {"sessionID": session, "target": args.target, "tags": SHARED_TAG},
        )
        if status == 200:
            print(f"Filed into collection {args.target}.")
        else:
            print(f"Saved, but could not move to {args.target} ({status}): {target_body[:200]}")
            print(f"Items are tagged '{SHARED_TAG}' so you can re-file them in one go.")

    if args.no_pdfs:
        return 0

    # saveItems echoes back the stored items, which is the only place the item
    # keys appear; they are needed to hang attachments off the right parents.
    try:
        saved = json.loads(body).get("items", [])
    except json.JSONDecodeError:
        saved = []
    keys = {(it.get("DOI") or "").lower(): it.get("key") for it in saved if it.get("key")}
    if not keys:
        print("\nCould not read item keys from Zotero's response; skipping attachments.")
        print("In Zotero, select the imported items and choose 'Find Available PDFs'.")
        return 0

    attached = 0
    for rec, item in zip(records, items):
        url = rec.get("pdf_url")
        key = keys.get((item["DOI"] or "").lower())
        if not url or not key:
            continue
        blob = download(url)
        if not blob:
            print(f"  [fail] {rec['key']:<16} download did not return a PDF")
            continue
        status, resp = post_attachment(session, key, url, blob)
        if status in (200, 201):
            attached += 1
            print(f"  [ok]   {rec['key']:<16} {len(blob) / 1e6:.1f} MB")
        else:
            print(f"  [fail] {rec['key']:<16} {status} {resp[:120]}")

    print(f"\nAttached {attached}/{len(records)} PDFs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
