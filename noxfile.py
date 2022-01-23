import nox


@nox.session(python=["3.9", "3.10"])
@nox.parametrize("django_ver", ["3.2.11"])
def tests(session, django_ver):
    session.run("poetry", "install", external=True)
    session.install(f"django=={django_ver}")
    session.run("pytest", "tests/")
