from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import matplotlib.patheffects as pe

__all__ = ["PipelineFigure", "generate_pipeline_figure"]

log = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("exploration/reports/project_pipeline.png")

BG      = "#F7F9FC"
ARROW_C = "#4B5E71"
LABEL_C = "#1A2535"
DESC_C  = "#536070"
TITLE_C = "#0D1B2A"
SUB_C   = "#607080"
FONT    = "DejaVu Sans"

PALETTE: dict[str, tuple[str, str]] = {
    "data":        ("#EAF3FF", "#6EAAEE"),
    "explore":     ("#E6F7FF", "#5BC0EB"),
    "etl":         ("#E8FBF0", "#5DBF85"),
    "database":    ("#FEF9E2", "#E8C13D"),
    "model_table": ("#FFF4D6", "#DDA827"),
    "baseline":    ("#F1EEFF", "#9B82E0"),
    "model":       ("#FDF0FA", "#D875B8"),
    "evaluation":  ("#FFEEEF", "#E8707A"),
    "reports":     ("#F2FCEA", "#90CC55"),
    "repro":       ("#F0F4F8", "#839AAF"),
}

@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float
    label: str
    icon: str          # single Unicode glyph, always renders in DejaVu / basic fonts
    icon_color: str    # accent colour for the icon
    desc: str
    color_key: str

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def right(self) -> tuple[float, float]:
        return (self.x + self.w, self.cy)

    def left(self) -> tuple[float, float]:
        return (self.x, self.cy)

    def top(self) -> tuple[float, float]:
        return (self.cx, self.y + self.h)

    def bottom(self) -> tuple[float, float]:
        return (self.cx, self.y)


@dataclass
class Arrow:
    start: tuple[float, float]
    end: tuple[float, float]
    rad: float = 0.0


@dataclass
class PipelineLayout:
    boxes: list[Box] = field(default_factory=list)
    arrows: list[Arrow] = field(default_factory=list)

    @classmethod
    def default(cls) -> "PipelineLayout":
        W  = 0.128   # standard box width
        H  = 0.098   # box height
        WS = 0.092   # narrow box (model table)

        R1 = 0.635   # top row  y
        R2 = 0.350   # mid row  y
        R3 = 0.082   # bot row  y

        GAP = 0.155
        x1  = [0.038 + i * GAP for i in range(4)]

        boxes = [
            Box(x1[0],         R1, W,  H,
                "Raw Data",     "⬡", "#6EAAEE", "Molecule pairs\nChEMBL source",    "data"),
            Box(x1[1],         R1, W,  H,
                "Exploration",  "◈", "#5BC0EB", "Quality checks\nBuild splits",     "explore"),
            Box(x1[2],         R1, W,  H,
                "ETL Pipeline", "⚙", "#5DBF85", "Import · Clean\nPair · Export",    "etl"),
            Box(x1[3],         R1, W,  H,
                "SQL Database", "⊞", "#E8C13D", "Molecules\nActivities · Pairs",    "database"),
            Box(x1[3]+W+0.010, R1, WS, H,
                "Model Table",  "◉", "#DDA827", "chembl_\nmodeling.csv",            "model_table"),

            Box(0.082, R2, W, H,
                "Baseline",   "△", "#9B82E0", "Sanity checks\nSimple heuristics", "baseline"),
            Box(0.330, R2, W, H,
                "Main Model", "⊛", "#D875B8", "SMILES + RDKit\nTrain classifier",  "model"),
            Box(0.577, R2, W, H,
                "Evaluation", "◎", "#E8707A", "Per-target\nPrecision first",       "evaluation"),

            Box(0.118, R3, W, H,
                "Reports",         "❖", "#90CC55", "JSON · Markdown\nPlots",      "reports"),
            Box(0.553, R3, W, H,
                "Reproducibility", "↺", "#839AAF", "CLI · Tests\nDocker · CI/CD", "repro"),
        ]

        raw, explore, etl, db, mt, base, model, evl, rep, repro = boxes

        arrows = [
            Arrow(raw.right(),     explore.left()),
            Arrow(explore.right(), etl.left()),
            Arrow(etl.right(),     db.left()),
            Arrow(db.right(),      mt.left()),

            # Model Table fans ↓ to modelling row
            Arrow(mt.bottom(), evl.top(),   rad=-0.30),
            Arrow(mt.bottom(), model.top(), rad= 0.04),

            # Baseline → Evaluation
            Arrow(base.right(), evl.left()),

            # Evaluation fans ↓ to output row
            Arrow(evl.bottom(), repro.top(), rad=-0.22),
            Arrow(evl.bottom(), rep.top(),   rad= 0.24),
        ]

        return cls(boxes=boxes, arrows=arrows)


class PipelineFigure:
    def __init__(
        self,
        layout: PipelineLayout | None = None,
        *,
        figsize: tuple[float, float] = (11.0, 6.0),
        dpi: int = 220,
    ) -> None:
        self.layout  = layout or PipelineLayout.default()
        self.figsize = figsize
        self.dpi     = dpi

    def save(self, output_path: Path) -> Path:
        """Render and save the figure; returns the resolved path."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig, ax = self._build()
        fig.savefig(output_path, dpi=self.dpi, bbox_inches="tight", facecolor=BG)
        plt.close(fig)
        log.info("Saved → %s", output_path)
        return output_path

    def _build(self) -> tuple[plt.Figure, plt.Axes]:
        fig, ax = plt.subplots(figsize=self.figsize)
        ax.set_xlim(0, 0.84)
        ax.set_ylim(0, 0.87)
        ax.axis("off")
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)

        self._draw_phase_bands(ax)
        self._draw_title(ax)
        self._draw_phase_labels(ax)

        # Arrows first so boxes sit on top
        for a in self.layout.arrows:
            self._draw_arrow(ax, a)
        for b in self.layout.boxes:
            self._draw_box(ax, b)

        fig.tight_layout(pad=0.3)
        return fig, ax

    @staticmethod
    def _draw_phase_bands(ax: plt.Axes) -> None:
        bands = [
            (0.588, 0.786, "#E8F3FF", 0.50),
            (0.302, 0.497, "#F3EEFF", 0.50),
            (0.034, 0.237, "#EDFAEE", 0.50),
        ]
        for y0, y1, c, alpha in bands:
            rect = FancyBboxPatch(
                (0.020, y0), 0.800, y1 - y0,
                boxstyle="round,pad=0.004,rounding_size=0.014",
                facecolor=c, alpha=alpha, edgecolor="none", zorder=0,
            )
            ax.add_patch(rect)

    @staticmethod
    def _draw_title(ax: plt.Axes) -> None:
        ax.text(0.42, 0.843,
                "Molecular Similarity — Pipeline Flowchart",
                ha="center", va="center",
                fontsize=13.0, fontweight="bold",
                color=TITLE_C, fontfamily=FONT,
                path_effects=[pe.withSimplePatchShadow(
                    shadow_rgbFace="#c8d6e0", alpha=0.35, rho=0.93)])
        ax.text(0.42, 0.812,
                "End-to-end pipeline: raw ChEMBL data  →  precision-focused molecular similarity classifier",
                ha="center", va="center",
                fontsize=8.0, color=SUB_C, fontfamily=FONT)

    @staticmethod
    def _draw_phase_labels(ax: plt.Axes) -> None:
        for x, y, txt in [
            (0.008, 0.687, "① Ingest"),
            (0.008, 0.399, "② Model"),
            (0.008, 0.136, "③ Output"),
        ]:
            ax.text(x, y, txt,
                    ha="left", va="center", fontsize=7.0,
                    color="#90A4AE", fontfamily=FONT,
                    fontstyle="italic", rotation=90)

    @staticmethod
    def _draw_box(ax: plt.Axes, box: Box) -> None:
        fill, border = PALETTE.get(box.color_key, ("#F0F4F8", "#9AAFBE"))

        # Drop shadow
        ax.add_patch(FancyBboxPatch(
            (box.x + 0.0022, box.y - 0.0022), box.w, box.h,
            boxstyle="round,pad=0.007,rounding_size=0.016",
            linewidth=0, facecolor="#B8C8D4", alpha=0.50, zorder=1,
        ))

        # Main box
        ax.add_patch(FancyBboxPatch(
            (box.x, box.y), box.w, box.h,
            boxstyle="round,pad=0.007,rounding_size=0.016",
            linewidth=1.1, edgecolor=border,
            facecolor=fill, zorder=2,
        ))

        # Coloured top-stripe accent
        ax.add_patch(FancyBboxPatch(
            (box.x + 0.008, box.y + box.h - 0.013), box.w - 0.016, 0.009,
            boxstyle="round,pad=0.001,rounding_size=0.003",
            linewidth=0, facecolor=border, alpha=0.65, zorder=3,
        ))

        # Icon 
        ax.text(box.cx, box.cy + 0.027, box.icon,
                ha="center", va="center",
                fontsize=13, color=box.icon_color,
                fontfamily=FONT,
                fontweight="bold", zorder=4)

        # Label
        ax.text(box.cx, box.cy - 0.004, box.label,
                ha="center", va="center",
                fontsize=7.5, fontweight="bold",
                color=LABEL_C, fontfamily=FONT, zorder=4)

        # Description
        if box.desc:
            ax.text(box.cx, box.cy - 0.030, box.desc,
                    ha="center", va="center",
                    fontsize=5.9, color=DESC_C,
                    fontfamily=FONT, linespacing=1.35, zorder=4)

    @staticmethod
    def _draw_arrow(ax: plt.Axes, arrow: Arrow) -> None:
        ax.add_patch(FancyArrowPatch(
            arrow.start, arrow.end,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=1.3,
            color=ARROW_C,
            connectionstyle=f"arc3,rad={arrow.rad}",
            zorder=1,
            shrinkA=3, shrinkB=3,
        ))


def generate_pipeline_figure(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    dpi: int = 220,
) -> Path:
    """Build the default layout, render and save it. Returns the output path."""
    return PipelineFigure(dpi=dpi).save(output_path)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate the Molecular Similarity pipeline flowchart.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT_PATH,
                   help="Destination PNG path.")
    p.add_argument("--dpi", type=int, default=220,
                   help="Output resolution (dots per inch).")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Enable INFO-level logging.")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s  %(message)s",
    )
    out = generate_pipeline_figure(args.output, dpi=args.dpi)
    print(f"Saved → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
