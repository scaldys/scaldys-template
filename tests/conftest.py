import pytest
import datetime


# def pytest_cmdline_preparse(args):
#     """Change the default base temporary directory by dynamically adding a command line parameter
#
#     See:
#         http://doc.pytest.org/en/latest/example/simple.html
#         http://doc.pytest.org/en/latest/tmpdir.html
#     """
#     basetemp = "_test_runs"
#     args[:] = ["--basetemp={0}".format(basetemp)] + args


@pytest.fixture(scope="session")
def temporary_test_directory(tmpdir_factory) -> str:
    timestamp = "{0:%Y-%m-%d_%H-%M-%S}".format(datetime.datetime.now())
    test_run_dir = str(
        tmpdir_factory.mktemp("testrun-{0}".format(timestamp), numbered=False)
    )
    return test_run_dir


@pytest.fixture(scope="session", autouse=True)
def setup_test_data_if_not_exist():
    # Code to run before all tests
    print("\n Setting up before all tests\n")
