from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path


PDB_PATTERN = re.compile(r"best_rocs_conformer_(\d{3})([ab])\.pdb$")
SVG_PATTERN = re.compile(r"image_molecule_(\d{3})([ab])\.svg$")


def _safe_mean(values: list[int]) -> float:
    return round(statistics.mean(values), 2) if values else 0.0


def _safe_median(values: list[int]) -> float:
    return round(statistics.median(values), 2) if values else 0.0


def _parse_element(line: str) -> str:
    element = line[76:78].strip()
    if element:
        return element

    atom_name = line[12:16].strip()
    letters = "".join(character for character in atom_name if character.isalpha())
    return letters[:2] if letters else "?"


def _parse_pdb_file(path: Path) -> dict[str, object]:
    atom_count = 0
    heavy_atom_count = 0
    element_counts: Counter[str] = Counter()
    compound_name = None

    with path.open() as handle:
        for line in handle:
            if line.startswith("COMPND") and compound_name is None:
                compound_name = line.split(maxsplit=1)[1].strip()
            if line.startswith(("ATOM", "HETATM")):
                atom_count += 1
                element = _parse_element(line)
                element_counts[element] += 1
                if element.upper() != "H":
                    heavy_atom_count += 1

    return {
        "compound_name": compound_name,
        "atom_count": atom_count,
        "heavy_atom_count": heavy_atom_count,
        "element_counts": dict(sorted(element_counts.items())),
    }


def _collect_files(directory: Path, pattern: re.Pattern[str]) -> dict[str, dict[str, Path]]:
    grouped: dict[str, dict[str, Path]] = {}

    for path in sorted(directory.glob("*")):
        match = pattern.match(path.name)
        if not match:
            continue
        identifier, variant = match.groups()
        grouped.setdefault(identifier, {})[variant] = path

    return grouped


def build_summary(dataset_root: Path) -> dict[str, object]:
    conformer_dir = dataset_root / "conformers_3D"
    image_dir = dataset_root / "images_2D"

    conformers = _collect_files(conformer_dir, PDB_PATTERN)
    images = _collect_files(image_dir, SVG_PATTERN)

    pdb_details: dict[str, dict[str, dict[str, object]]] = {}
    atom_counts: list[int] = []
    heavy_atom_counts: list[int] = []
    element_counts: Counter[str] = Counter()

    for identifier, variants in conformers.items():
        pdb_details[identifier] = {}
        for variant, path in variants.items():
            parsed = _parse_pdb_file(path)
            pdb_details[identifier][variant] = parsed
            atom_counts.append(int(parsed["atom_count"]))
            heavy_atom_counts.append(int(parsed["heavy_atom_count"]))
            element_counts.update(parsed["element_counts"])

    complete_pdb_pairs = sorted(
        identifier for identifier, variants in conformers.items() if {"a", "b"} <= set(variants)
    )
    complete_image_pairs = sorted(
        identifier for identifier, variants in images.items() if {"a", "b"} <= set(variants)
    )
    complete_joint_pairs = sorted(set(complete_pdb_pairs) & set(complete_image_pairs))

    summary = {
        "dataset_root": str(dataset_root),
        "folders": {
            "conformers_3D": str(conformer_dir),
            "images_2D": str(image_dir),
        },
        "counts": {
            "pdb_files": sum(len(variants) for variants in conformers.values()),
            "svg_files": sum(len(variants) for variants in images.values()),
            "indexed_pdb_groups": len(conformers),
            "indexed_svg_groups": len(images),
            "complete_pdb_pairs": len(complete_pdb_pairs),
            "complete_svg_pairs": len(complete_image_pairs),
            "complete_joint_pairs": len(complete_joint_pairs),
        },
        "pairing": {
            "missing_pdb_variants": sorted(
                identifier
                for identifier, variants in conformers.items()
                if set(variants) != {"a", "b"}
            ),
            "missing_svg_variants": sorted(
                identifier
                for identifier, variants in images.items()
                if set(variants) != {"a", "b"}
            ),
        },
        "pdb_statistics": {
            "atom_count": {
                "min": min(atom_counts) if atom_counts else 0,
                "max": max(atom_counts) if atom_counts else 0,
                "mean": _safe_mean(atom_counts),
                "median": _safe_median(atom_counts),
            },
            "heavy_atom_count": {
                "min": min(heavy_atom_counts) if heavy_atom_counts else 0,
                "max": max(heavy_atom_counts) if heavy_atom_counts else 0,
                "mean": _safe_mean(heavy_atom_counts),
                "median": _safe_median(heavy_atom_counts),
            },
            "element_frequencies": dict(element_counts.most_common()),
        },
        "examples": {
            "first_complete_pair": {
                "pair_id": complete_joint_pairs[0] if complete_joint_pairs else None,
                "pdb": {
                    variant: str(conformers[complete_joint_pairs[0]][variant])
                    for variant in ("a", "b")
                }
                if complete_joint_pairs
                else {},
                "svg": {
                    variant: str(images[complete_joint_pairs[0]][variant])
                    for variant in ("a", "b")
                }
                if complete_joint_pairs
                else {},
            },
            "first_pdb_record": pdb_details.get(complete_joint_pairs[0], {}) if complete_joint_pairs else {},
        },
    }

    return summary


def render_markdown(summary: dict[str, object]) -> str:
    counts = summary["counts"]
    pairing = summary["pairing"]
    pdb_statistics = summary["pdb_statistics"]
    first_pair = summary["examples"]["first_complete_pair"]

    lines = [
        "# Dataset Summary",
        "",
        f"- Dataset root: `{summary['dataset_root']}`",
        f"- PDB files: {counts['pdb_files']}",
        f"- SVG files: {counts['svg_files']}",
        f"- Indexed molecule groups: {counts['indexed_pdb_groups']}",
        f"- Complete paired entries across both modalities: {counts['complete_joint_pairs']}",
        "",
        "## Pairing Checks",
        "",
        f"- Missing PDB variants: {len(pairing['missing_pdb_variants'])}",
        f"- Missing SVG variants: {len(pairing['missing_svg_variants'])}",
        "",
        "## PDB Statistics",
        "",
        (
            "- Atom count per conformer: "
            f"min={pdb_statistics['atom_count']['min']}, "
            f"median={pdb_statistics['atom_count']['median']}, "
            f"mean={pdb_statistics['atom_count']['mean']}, "
            f"max={pdb_statistics['atom_count']['max']}"
        ),
        (
            "- Heavy atom count per conformer: "
            f"min={pdb_statistics['heavy_atom_count']['min']}, "
            f"median={pdb_statistics['heavy_atom_count']['median']}, "
            f"mean={pdb_statistics['heavy_atom_count']['mean']}, "
            f"max={pdb_statistics['heavy_atom_count']['max']}"
        ),
        "",
        "## Most Common Elements",
        "",
    ]

    for element, count in list(pdb_statistics["element_frequencies"].items())[:10]:
        lines.append(f"- {element}: {count}")

    lines.extend(
        [
            "",
            "## Example Pair",
            "",
            f"- Pair id: {first_pair['pair_id']}",
            f"- PDB a: `{first_pair['pdb'].get('a', '')}`",
            f"- PDB b: `{first_pair['pdb'].get('b', '')}`",
            f"- SVG a: `{first_pair['svg'].get('a', '')}`",
            f"- SVG b: `{first_pair['svg'].get('b', '')}`",
            "",
        ]
    )

    return "\n".join(lines)


def render_html(summary: dict[str, object]) -> str:
    counts = summary["counts"]
    atom_stats = summary["pdb_statistics"]["atom_count"]
    heavy_stats = summary["pdb_statistics"]["heavy_atom_count"]

    metrics = [
        ("PDB files", counts["pdb_files"], max(counts["pdb_files"], counts["svg_files"], 1)),
        ("SVG files", counts["svg_files"], max(counts["pdb_files"], counts["svg_files"], 1)),
        ("Joint pairs", counts["complete_joint_pairs"], max(counts["complete_joint_pairs"], 1)),
        ("Median atoms", atom_stats["median"], max(atom_stats["max"], 1)),
        ("Median heavy atoms", heavy_stats["median"], max(heavy_stats["max"], 1)),
    ]

    bars = []
    for label, value, maximum in metrics:
        width = round((float(value) / float(maximum)) * 100, 2)
        bars.append(
            f"""
            <div class="metric">
              <div class="metric-header">
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
              <div class="bar-track">
                <div class="bar-fill" style="width: {width}%;"></div>
              </div>
            </div>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Molecular Similarity Dataset Overview</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f3efe6;
      --card: #fffaf2;
      --ink: #1f2a2e;
      --muted: #59686d;
      --accent: #126e61;
      --accent-soft: #d8efe8;
      --line: #d8d2c6;
    }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(18, 110, 97, 0.12), transparent 28%),
        linear-gradient(180deg, #f8f4ec 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    main {{
      max-width: 900px;
      margin: 0 auto;
      padding: 48px 24px 72px;
    }}
    .hero, .card {{
      background: rgba(255, 250, 242, 0.9);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 18px 60px rgba(31, 42, 46, 0.08);
    }}
    .hero {{
      padding: 28px;
      margin-bottom: 24px;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 0.76rem;
      color: var(--accent);
      margin-bottom: 10px;
    }}
    h1, h2 {{
      margin: 0 0 12px;
    }}
    p {{
      color: var(--muted);
      line-height: 1.6;
    }}
    .grid {{
      display: grid;
      gap: 24px;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }}
    .card {{
      padding: 24px;
    }}
    .metric {{
      margin-bottom: 18px;
    }}
    .metric-header {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
      color: var(--muted);
    }}
    .bar-track {{
      height: 14px;
      border-radius: 999px;
      background: #e8e1d6;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #126e61 0%, #3f9d8f 100%);
    }}
    code {{
      font-family: "SFMono-Regular", "Menlo", monospace;
      font-size: 0.95em;
    }}
    ul {{
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.7;
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="eyebrow">Dataset overview</div>
      <h1>Molecular Similarity Training Set</h1>
      <p>{summary["dataset_root"]}</p>
      <p>This quick visual report summarizes dataset completeness and a few basic 3D conformer statistics so we can decide the next analysis step with confidence.</p>
    </section>
    <section class="grid">
      <article class="card">
        <h2>Core Metrics</h2>
        {''.join(bars)}
      </article>
      <article class="card">
        <h2>What We Learned</h2>
        <ul>
          <li>{counts["complete_joint_pairs"]} molecule indices have both 3D conformers and 2D images for variants <code>a</code> and <code>b</code>.</li>
          <li>The median conformer contains {atom_stats["median"]} atoms and {heavy_stats["median"]} heavy atoms.</li>
          <li>The dataset is organized as paired entries, which is a good fit for similarity learning or Siamese-style modeling.</li>
        </ul>
      </article>
    </section>
  </main>
</body>
</html>
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/explore_dataset.py /path/to/dataset")
        return 1

    dataset_root = Path(sys.argv[1]).expanduser().resolve()
    if not dataset_root.exists():
        print(f"Dataset directory not found: {dataset_root}")
        return 1

    reports_dir = Path("exploration/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary = build_summary(dataset_root)
    summary_json = reports_dir / "dataset_summary.json"
    summary_md = reports_dir / "dataset_summary.md"
    summary_html = reports_dir / "dataset_overview.html"

    summary_json.write_text(json.dumps(summary, indent=2))
    summary_md.write_text(render_markdown(summary))
    summary_html.write_text(render_html(summary))

    print(f"Wrote {summary_json}")
    print(f"Wrote {summary_md}")
    print(f"Wrote {summary_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
