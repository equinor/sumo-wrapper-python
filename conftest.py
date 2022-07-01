def pytest_addoption(parser):
    parser.addoption("--token", action="store", default="")

def pytest_generate_tests(metafunc):
    token = metafunc.config.option.token
    token = token if len(token) > 0 else None

    if "token" in metafunc.fixturenames:
        metafunc.parametrize("token", [token])