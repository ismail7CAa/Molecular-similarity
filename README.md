# Molecular-similarity

Initial repository scaffold for the Molecular-similarity project.

## Local Environment

1. Create the virtual environment:
   `python3 -m venv .venv`
2. Activate it:
   `source .venv/bin/activate`
3. Install the project with development dependencies:
   `pip install -e .[dev]`
4. Copy the environment template if needed:
   `cp .env.example .env`

## CI/CD

This repository includes a starter GitHub Actions pipeline in
`.github/workflows/ci-cd.yml`.

- CI runs on pushes and pull requests.
- CD builds and uploads distribution artifacts on version tags like `v0.1.0`.
- The workflow is intentionally defensive while the project is still being
  scaffolded, so it skips dependency installation and tests when the relevant
  files do not exist yet.
