import pytest
import subprocess
import sys
import tempfile

cbdep_install_tests = [
    ["uv", "0.4.29", "unknown-linux-gnu"],
    ["openjdk", "9.0.4+11"],
    ["openjdk", "8u282-b08"],
    ["openjdk", "11.0.9.1+1"],
    ["openjdk", "11.0.9+11"],
    # openjdk with a dotted build number (CBD-5669)
    ["openjdk", "17.0.9+9.1", "windows"],
    ["openjdk-jre", "9.0.4+11"],
    ["openjdk-jre", "8u282-b08"],
    ["openjdk-jre", "11.0.9.1+1"],
    ["openjdk-jre", "11.0.9+11"],
    ["corretto", "11.0.21.9.1"],
    ["python", "3.9.1"],
    ["miniforge3", "22.9.0-1"],
    ["mambaforge", "4.13.0-1"],
    ["miniconda3-py38", "4.12.0"],
    ["miniconda3-py39", "4.12.0"],
    ["miniconda2", "4.5.11"],
    ["cmake", "3.25.0-rc4"],
    ["cmake", "3.24.3"],
    ["ninja", "1.11.1"],
    # check_one_package wix 3.11.2 windows # windows only
    ["jq", "1.7"],
    ["helm", "3.17.0"],
    ["flux", "2.5.1"],
    ["prometheus", "2.40.1"],
    ["golang", "1.19.3"],
    ["dotnet-core-sdk", "7.0.100"],
    ["dotnet-core-runtime", "6.0.11"],
    ["docker", "20.10.21"],
    ["nodejs", "18.12.1"],
    # check_one_package php 7.3.4-cb1 - legacy package, can't find any installation candidates?
    ["php-nts", "8.1.4-cb1"],
    ["php-zts", "8.1.4-cb1"],
    ["libcouchbase_vc11", "2.9.5", "windows"],
    ["libcouchbase_vc14", "3.0.0", "windows"],
    ["couchbasemock", "1.5.25"],
    ["analytics-jars", "7.0.5-7643"],
]

install_dir = tempfile.TemporaryDirectory()

class TestCbdepInstall:

    @pytest.fixture(params=cbdep_install_tests)
    def args(self, request):
        return request.param

    def test_cbdep_install(self, args):

        if len(args) > 2:
            platform = args[2]
        else:
            platform = "macosx" if sys.platform == "darwin" else "linux"

        subprocess.run(
            [
                "uv", "run", "cbdep",
                "--platform", platform,
                "install", "-d", install_dir.name, args[0], args[1]
            ],
            check=True
        )
