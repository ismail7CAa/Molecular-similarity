# Why Docker

We added Docker to make the project easier to run outside the local environment.

The project uses RDKit, scikit-learn, matplotlib, and generated reports. Those dependencies can be sensitive to Python versions and local machine state. Docker gives us a repeatable container path for running the default smoke workflow.

Docker is useful for:

- Reproducing the pipeline figure generation.
- Checking that package installation works cleanly.
- Sharing the project without asking another machine to match the local setup.
- Reducing environment drift between local development and CI-like runs.

The container is not the whole project story, but it is a practical reproducibility layer.

