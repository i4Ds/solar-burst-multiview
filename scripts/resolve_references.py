"""Resolve the Sharma et al. (2022) references this pipeline depends on.

Each entry is matched against Crossref by bibliographic string, then checked
against the journal/volume/page recorded in the paper's reference list before
being accepted. Unverified matches are reported rather than written, since a
plausible-looking wrong DOI is worse than a gap.

    python scripts/resolve_references.py            # resolve and write BibTeX
    python scripts/resolve_references.py --report   # show matches, write nothing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

CROSSREF = "https://api.crossref.org/works"
MAILTO = "solar-burst-multiview@fhnw.ch"
OUTDIR = Path(__file__).resolve().parent.parent / "references"


@dataclass
class Reference:
    """A reference plus the facts needed to verify a Crossref match.

    Searching on the title rather than the abbreviated journal citation matters:
    the short form pulls back neighbouring articles in the same volume, and two
    of these references sit one page apart in ApJ 875.
    """

    key: str
    first_author: str
    title: str
    year: int
    role: str
    journal: str = ""
    volume: str | None = None
    page: str | None = None
    unresolvable: bool = False
    tags: list[str] = field(default_factory=list)

    @property
    def citation(self) -> str:
        bits = [self.first_author, str(self.year), self.title, self.journal]
        return ", ".join(b for b in bits if b)


# The references the implementation actually rests on, grouped by the pipeline
# stage that needs them. `role` is carried into Zotero as a note so the reason
# each paper is here survives outside this file.
REFERENCES: list[Reference] = [
    Reference(
        key="sharma2022",
        first_author="Sharma",
        title="Detection of Ubiquitous Weak and Impulsive Nonthermal Emissions from the Solar Corona",
        journal="The Astrophysical Journal",
        year=2022,
        volume="937",
        page="99",
        role="The paper being reproduced.",
        tags=["target-paper"],
    ),
    Reference(
        key="oberoi2017",
        first_author="Oberoi",
        title="Estimating Solar Flux Density at Low Radio Frequencies Using a Sky Brightness Model",
        journal="Solar Physics",
        year=2017,
        volume="292",
        page="75",
        role="Absolute solar flux density calibration prescription (Section 3.1).",
        tags=["flux-calibration"],
    ),
    Reference(
        key="mohan2017",
        first_author="Mohan",
        title="4D Data Cubes from Radio-Interferometric Spectroscopic Snapshot Imaging",
        journal="Solar Physics",
        year=2017,
        volume="292",
        page="168",
        role="Conversion from Jy/beam to brightness temperature (Sections 3.2, 4.2).",
        tags=["brightness-temperature"],
    ),
    Reference(
        key="mondal2019",
        first_author="Mondal",
        title="Unsupervised Generation of High Dynamic Range Solar Images: A Novel Algorithm for Self-calibration of Interferometry Data",
        journal="The Astrophysical Journal",
        year=2019,
        volume="875",
        page="97",
        role="AIRCARS: high-dynamic-range solar self-calibration and snapshot imaging pipeline.",
        tags=["calibration", "imaging"],
    ),
    Reference(
        key="mondal2020a",
        first_author="Mondal",
        title="First Radio Evidence for Impulsive Heating Contribution to the Quiet Solar Corona",
        journal="The Astrophysical Journal Letters",
        year=2020,
        volume="895",
        page="L39",
        role="The weak quiet-Sun impulsive emissions this paper independently confirms.",
        tags=["science-target"],
    ),
    Reference(
        key="kansabanik2022",
        first_author="Kansabanik",
        title="Tackling the Unique Challenges of Low-frequency Solar Polarimetry with the Square Kilometre Array Low Precursor: The Algorithm",
        journal="The Astrophysical Journal",
        year=2022,
        volume="932",
        page="110",
        role="P-AIRCARS, the successor solar imaging pipeline; reference for calibration strategy.",
        tags=["calibration", "imaging"],
    ),
    Reference(
        key="suresh2017",
        first_author="Suresh",
        title="Wavelet-based Characterization of Small-scale Solar Emission Features at Low Radio Frequencies",
        journal="The Astrophysical Journal",
        year=2017,
        volume="843",
        page="19",
        role="Weak burst durations and the ~5 MHz bandwidth assumed for burst energetics.",
        tags=["burst-statistics"],
    ),
    Reference(
        key="sharma2018",
        first_author="Sharma",
        title="Quantifying Weak Nonthermal Solar Radio Emission at Low Radio Frequencies",
        journal="The Astrophysical Journal",
        year=2018,
        volume="852",
        page="69",
        role="Decomposition into slowly varying and impulsive components; basis of the subtraction model.",
        tags=["visibility-subtraction"],
    ),
    Reference(
        key="sharma2020",
        first_author="Sharma",
        title="Propagation Effects in Quiet Sun Observations at Meter Wavelengths",
        journal="The Astrophysical Journal",
        year=2020,
        volume="903",
        page="126",
        role="Coronal scattering and refraction; explains burst/EUV positional offsets and size dilution.",
        tags=["interpretation"],
    ),
    Reference(
        key="newkirk1961",
        first_author="Newkirk",
        title="The Solar Corona in Active Regions and the Thermal Origin of the Slowly Varying Component of Solar Radio Radiation",
        journal="The Astrophysical Journal",
        year=1961,
        volume="133",
        page="983",
        role="Coronal density model mapping observing frequency to coronal height (15-150 Mm).",
        tags=["coronal-model"],
    ),
    Reference(
        key="kulkarni1989",
        first_author="Kulkarni",
        title="Self-noise in interferometers: radio and infrared",
        journal="The Astronomical Journal",
        year=1989,
        volume="98",
        page="1112",
        role="Self-noise formalism; sets the noise floor for weak burst detection.",
        tags=["noise"],
    ),
    Reference(
        key="morgan2021",
        first_author="Morgan",
        title="A measurement of source noise at low frequency: Implications for modern low frequency arrays",
        journal="Publications of the Astronomical Society of Australia",
        year=2021,
        volume="38",
        page="e013",
        role="Self-noise for large-N interferometers; correlated across baselines.",
        tags=["noise"],
    ),
    Reference(
        key="tingay2013",
        first_author="Tingay",
        title="The Murchison Widefield Array: The Square Kilometre Array Precursor at Low Radio Frequencies",
        journal="Publications of the Astronomical Society of Australia",
        year=2013,
        volume="30",
        page="e007",
        role="MWA Phase-I instrument description.",
        tags=["instrument"],
    ),
    Reference(
        key="lonsdale2009",
        first_author="Lonsdale",
        title="The Murchison Widefield Array: Design Overview",
        journal="Proceedings of the IEEE",
        year=2009,
        volume="97",
        page="1497",
        role="MWA design and array configuration.",
        tags=["instrument"],
    ),
    Reference(
        key="garton2018",
        first_author="Garton",
        title="Automated coronal hole identification via multi-thermal intensity segmentation",
        journal="Journal of Space Weather and Space Climate",
        year=2018,
        volume="8",
        page="A02",
        role="CHIMERA coronal hole detection, needed for the Figure 1 boundary contours.",
        tags=["figure-1"],
    ),
    Reference(
        key="pesnell2012",
        first_author="Pesnell",
        title="The Solar Dynamics Observatory (SDO)",
        journal="Solar Physics",
        year=2012,
        volume="275",
        page="3",
        role="SDO/AIA and HMI, the EUV and magnetogram source for Figures 1, 9, 11, 12.",
        tags=["figure-1", "instrument"],
    ),
    Reference(
        key="gibson2016",
        first_author="Gibson",
        title="FORWARD: A Toolset for Multiwavelength Coronal Magnetometry",
        journal="Frontiers in Astronomy and Space Sciences",
        year=2016,
        volume="3",
        page="8",
        role="FORWARD coronal model used for the density/temperature/field profiles.",
        tags=["coronal-model"],
    ),
    Reference(
        key="reid2018",
        first_author="Reid",
        title="Spatial Expansion and Speeds of Type III Electron Beam Sources in the Solar Corona",
        journal="The Astrophysical Journal",
        year=2018,
        volume="867",
        page="158",
        role="Type-III electron beam energy estimate used as an independent energetics cross-check.",
        tags=["energetics"],
    ),
    Reference(
        key="hudson1991",
        first_author="Hudson",
        title="Solar flares, microflares, nanoflares, and coronal heating",
        journal="Solar Physics",
        year=1991,
        volume="133",
        page="357",
        role="The slope < -2 criterion for flare distributions to sustain coronal heating.",
        tags=["energetics"],
    ),
    Reference(
        key="parker1988",
        first_author="Parker",
        title="Nanoflares and the solar X-ray corona",
        journal="The Astrophysical Journal",
        year=1988,
        volume="330",
        page="474",
        role="The nanoflare hypothesis that frames the whole result.",
        tags=["framing"],
    ),
    # Conference proceedings with no reliable Crossref record. Kept in the list
    # so the gap is explicit rather than silently missing.
    Reference(
        key="mcmullin2007",
        first_author="McMullin",
        title="CASA Architecture and Applications",
        journal="ASP Conference Series 376",
        year=2007,
        volume="376",
        page="127",
        role="CASA, the imaging package used by the original paper.",
        unresolvable=True,
        tags=["software"],
    ),
]


def crossref_query(citation: str, rows: int = 20, by_title: bool = False) -> list[dict]:
    field = "query.title" if by_title else "query.bibliographic"
    params = urllib.parse.urlencode({field: citation, "rows": rows, "mailto": MAILTO})
    req = urllib.request.Request(
        f"{CROSSREF}?{params}", headers={"User-Agent": f"solar-burst-multiview (mailto:{MAILTO})"}
    )
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.load(fh)["message"]["items"]


def _norm(value) -> str:
    """Normalise for comparison. Missing values must fall back to empty, not 'none'."""
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def verify(item: dict, ref: Reference) -> tuple[bool, str]:
    """Accept a Crossref hit only if every fact we hold about it agrees.

    Every available check must pass. Matching on any single field is not enough:
    Mondal et al. (2019) and Mohan et al. (2019) are one page apart in ApJ 875,
    so a volume-only match silently returns the wrong paper.
    """
    parts = (item.get("issued", {}).get("date-parts") or [[None]])[0]
    year = parts[0] if parts else None
    if year is None or abs(int(year) - ref.year) > 1:
        return False, f"year {year} != {ref.year}"

    surnames = {_norm(a.get("family", "")) for a in item.get("author", []) or []}
    if surnames and _norm(ref.first_author) not in surnames:
        return False, f"author {ref.first_author} not among {sorted(s for s in surnames if s)[:4]}"

    got_title = _norm((item.get("title") or [""])[0])
    want_title = _norm(ref.title)
    # Compare on a prefix: Crossref sometimes carries a subtitle we do not have.
    n = min(len(got_title), len(want_title), 40)
    if n < 10 or got_title[:n] != want_title[:n]:
        return False, f"title mismatch: got {(item.get('title') or [''])[0][:60]!r}"

    if ref.volume and _norm(item.get("volume")) != _norm(ref.volume):
        return False, f"volume {item.get('volume')} != {ref.volume}"

    if ref.page:
        pages = _norm(item.get("page")) or _norm(item.get("article-number"))
        want = _norm(ref.page)
        if pages and not (pages.startswith(want) or want.startswith(pages)):
            return False, f"page {item.get('page') or item.get('article-number')} != {ref.page}"

    return True, "ok"


def bibtex_for(doi: str) -> str:
    req = urllib.request.Request(
        f"https://doi.org/{urllib.parse.quote(doi)}",
        headers={"Accept": "application/x-bibtex", "User-Agent": f"solar-burst-multiview (mailto:{MAILTO})"},
    )
    with urllib.request.urlopen(req, timeout=60) as fh:
        return fh.read().decode("utf-8").strip()


def resolve(ref: Reference) -> dict:
    record = {
        "key": ref.key,
        "citation": ref.citation,
        "role": ref.role,
        "tags": ref.tags,
        "status": "pending",
        "doi": None,
        "title": None,
        "container": None,
        "note": "",
    }

    if ref.unresolvable:
        record.update(status="manual", note="No Crossref record (conference proceedings)")
        return record

    # Full citation first; fall back to a title-only search, which does better
    # for instrument papers whose titles recur across conference proceedings.
    hits: list[dict] = []
    for by_title in (False, True):
        try:
            hits = crossref_query(ref.title if by_title else ref.citation, by_title=by_title)
        except Exception as exc:
            record.update(status="error", note=f"Crossref query failed: {exc}")
            return record

        for item in hits:
            ok, why = verify(item, ref)
            if ok:
                record.update(
                    status="verified",
                    doi=item.get("DOI"),
                    title=(item.get("title") or [None])[0],
                    container=(item.get("container-title") or [None])[0],
                    note=why if not by_title else "ok (title search)",
                )
                return record
        time.sleep(0.3)

    if hits:
        top = hits[0]
        _, why = verify(top, ref)
        record.update(
            status="unverified",
            doi=top.get("DOI"),
            title=(top.get("title") or [None])[0],
            container=(top.get("container-title") or [None])[0],
            note=f"best hit rejected: {why}",
        )
    else:
        record.update(status="notfound", note="no Crossref hits")
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="resolve and print only; write nothing")
    args = ap.parse_args()

    records = []
    for ref in REFERENCES:
        rec = resolve(ref)
        records.append(rec)
        mark = {"verified": "ok", "manual": "--", "unverified": "??", "notfound": "!!", "error": "!!"}[rec["status"]]
        print(f"[{mark}] {rec['key']:<16} {rec['doi'] or '-':<34} {(rec['title'] or rec['note'])[:70]}")
        time.sleep(0.3)

    verified = [r for r in records if r["status"] == "verified"]
    print(
        f"\n{len(verified)}/{len(records)} verified, "
        f"{sum(r['status'] == 'unverified' for r in records)} unverified, "
        f"{sum(r['status'] in ('notfound', 'error') for r in records)} failed, "
        f"{sum(r['status'] == 'manual' for r in records)} manual"
    )

    if args.report:
        return 0

    OUTDIR.mkdir(exist_ok=True)
    (OUTDIR / "resolution_report.json").write_text(json.dumps(records, indent=2) + "\n")

    entries = []
    for rec in verified:
        try:
            entries.append(f"% {rec['key']}: {rec['role']}\n{bibtex_for(rec['doi'])}")
        except Exception as exc:
            rec["status"] = "bibtex-failed"
            rec["note"] = str(exc)
            print(f"  bibtex failed for {rec['key']}: {exc}")
        time.sleep(0.3)

    (OUTDIR / "core_references.bib").write_text(
        "% Core references for reproducing Sharma et al. (2022), ApJ 937, 99.\n"
        "% Generated by scripts/resolve_references.py -- do not edit by hand.\n\n"
        + "\n\n".join(entries)
        + "\n"
    )
    print(f"\nwrote {OUTDIR / 'core_references.bib'} ({len(entries)} entries)")
    print(f"wrote {OUTDIR / 'resolution_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
