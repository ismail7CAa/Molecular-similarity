# Major Bugs And Fixes

## Committed Virtual Environment

At one point, a local virtual environment was committed into the repository. That made the repository noisy and could have broken CI by adding machine-specific files.

Fix:

- Removed the committed virtual environment from the tracked project scope.
- Updated ignore rules so local environments stay local.

## Small Dataset AUROC Looked Misleading

The first AUROC figures were technically valid but visually unhelpful because the original test split was too small. The curves had very few distinct threshold steps.

Fix:

- Removed the small-dataset AUROC figures.
- Kept AUROC evaluation on the larger ChEMBL export where the test split is meaningful.

## Long Target Names In Figures

Some target names were too long for plot labels and made the figures hard to read.

Fix:

- Wrapped target labels in the SQL precision plots.
- Reduced label font sizes.
- Regenerated the affected figures.

## Matplotlib Cache Warnings

Matplotlib warned that the default user cache directory was not writable in this environment.

Fix:

- The workflow already sets `MPLBACKEND=Agg` in CI/Docker contexts.
- Local report generation still succeeds by using a temporary matplotlib cache.

