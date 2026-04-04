# Molecular-similarity

Initial repository scaffold for the Molecular-similarity project.

## CI/CD

This repository includes a starter GitHub Actions pipeline in
`.github/workflows/ci-cd.yml`.

- CI runs on pushes and pull requests.
- CD builds and uploads distribution artifacts on version tags like `v0.1.0`.
- The workflow is intentionally defensive while the project is still being
  scaffolded, so it skips dependency installation and tests when the relevant
  files do not exist yet.
