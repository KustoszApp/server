import nox


@nox.session
def lint(session):
    """Run pre-commit linting."""
    session.install("pre-commit")
    # See https://github.com/theacodes/nox/issues/545
    # and https://github.com/pre-commit/pre-commit/issues/2178#issuecomment-1002163763
    session.run(
        "pre-commit",
        "run",
        "--all-files",
        "--show-diff-on-failure",
        "--hook-stage=manual",
        env={"SETUPTOOLS_USE_DISTUTILS": "stdlib"},
        *session.posargs,
    )


@nox.session(python=["3.9", "3.10"])
@nox.parametrize("django_ver", ["3.2.15", "4.0.7"])
def tests(session, django_ver):
    session.run("poetry", "install", "--no-interaction", external=True)
    session.install(f"django=={django_ver}")
    session.run("pytest", "tests/")
