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


@nox.session
@nox.parametrize(
    "python,django_ver",
    [
        (python, django_ver)
        for python in ("3.11", "3.12", "3.13", "3.14")
        for django_ver in ("4.2.27", "5.2.10", "6.0.1")
        if not (python == "3.11" and django_ver.startswith("6"))
    ],
)
def tests(session, django_ver):
    session.run(
        "poetry", "install", "--no-interaction", "--extras", "test", external=True
    )
    session.install(f"django=={django_ver}")
    session.run("pytest", "tests/")
