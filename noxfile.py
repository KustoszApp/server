import nox


@nox.session
def lint(session):
    """Run pre-commit linting."""
    session.install("pre-commit")
    session.run(
        "pre-commit",
        "run",
        "--all-files",
        "--show-diff-on-failure",
        "--hook-stage=manual",
        *session.posargs,
    )


@nox.session(python=["3.9", "3.10"])
@nox.parametrize("django_ver", ["3.2.18", "4.0.10", "4.1.7"])
def tests(session, django_ver):
    session.run(
        "poetry", "install", "--no-interaction", "--with", "test", external=True
    )
    session.install(f"django=={django_ver}")
    session.run("pytest", "tests/")
