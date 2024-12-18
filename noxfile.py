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


@nox.session(python=["3.11", "3.12", "3.13"])
@nox.parametrize("django_ver", ["4.2.17", "5.0.10", "5.1.4"])
def tests(session, django_ver):
    session.run(
        "poetry", "install", "--no-interaction", "--with", "test", external=True
    )
    session.install(f"django=={django_ver}")
    session.run("pytest", "tests/")
