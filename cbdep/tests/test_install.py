import logging
import os
import sys
import pytest
import tempfile
from hashlib import md5
from pathlib import Path
from shutil import rmtree
sys.path.append('../scripts')
from cache import Cache
from install import Installer
import platform_introspection as plat

wrong_platform_package = {
    "name": "java",
    "platform": "stegosaurus",
    "version": "11.0.3",
    "filename": "jdk-11.0.3_linux-x64_bin.tar.gz",
    "hash": "9bdefa0ac6378798643934ea6a065fe1"
}

missing_package = {
    "name": "foo",
    "platform": "linux",
    "version": "0.0.0",
    "hash": "0000",
}

def package_name(package):
    return package.get("name")

install_packages = [
    {
        "name": "dotnet-core-runtime",
        "platform": "linux",
        "version": "5.0.10",
        "arch": "x64",
        "filename": "dotnet-runtime-5.0.10-linux-x64.tar.gz",
        "hash": "ccd32f9a26d3f3d019ed00b9d0887efc",
        "final_file": "dotnet"
    },
    {
        # Something for Alpine
        "name": "dotnet-core-runtime",
        "platform": "linux",
        "version": "6.0.0",
        "arch": "x64-alpine",
        "filename": "dotnet-runtime-6.0.0-linux-musl-x64.tar.gz",
        "hash": "e37e167862f9bbc5735a8087d33d48c8",
        "final_file": "dotnet"
    },
    {
        "name": "golang",
        "platform": "linux",
        "arch": "amd64",
        "version": "1.16.5",
        "filename": "go1.16.5.linux-amd64.tar.gz",
        "install_dir": "go1.16.5",
        "hash": "76ff30daf15ef09e10a54be7b8a5f01b",
        "final_file": "bin/go"
    },
    {
        # random cbdep
        "name": "analytics-jars",
        "base_url": "https://packages.couchbase.com/releases",
        "platform": "linux",
        "version": "7.0.2-6512",
        "hash": "0bbb2376f42848451b6898247aa85793",
        "final_file": "jars/ini4j-0.5.4.jar"
    },
    {
        "name": "openjdk",
        "platform": "linux",
        "version": "11.0.12+7",
        "filename": "OpenJDK11U-jdk_x64_linux_hotspot_11.0.12_7.tar.gz",
        "hash": "4402d15b299b48172d1577b374392e63",
        "final_file": "bin/java"
    },
    {
        # MB-54306: openjdk with optional version segment
        "name": "openjdk",
        "platform": "linux",
        "version": "11.0.16.1+1",
        "filename": "OpenJDK11U-jdk_x64_linux_hotspot_11.0.16.1_1.tar.gz",
        "hash": "251cbce7b80e8fdcb48285867bba77d6",
        "final_file": "bin/java"
    },
    {
        # CBD-5669: openjdk with rebuild number
        "name": "openjdk",
        "platform": "windows",
        "version": "17.0.9+9.1",
        "filename": "OpenJDK17U-jdk_x64_windows_hotspot_17.0.9_9.zip",
        "hash": "4e45d6412a88b2dbef88d5391d533a46",
        "final_file": "bin/java.exe"
    },
    {
        # classic cbdep - also tests padding of version_bits
        "name": "icu4c",
        "base_url": "https://packages.couchbase.com/couchbase-server/deps",
        "platform": "amzn2",
        "version": "59.1-cb2",
        "filename": "icu4c-amzn2-x86_64-59.1-cb2.tgz",
        "hash": "6e95a3aa1dcd0f38c10596244e500c9d",
        "final_file": "include/unicode/ustring.h"
    },
    {
        # classic cbdep with "profile" extension in version number
        "name": "curl",
        "base_url": "https://packages.couchbase.com/couchbase-server/deps",
        "platform": "linux",
        "version": "8.4.0-1_openssl31x",
        "filename": "curl-linux-x86_64-8.4.0-1_openssl31x.tgz",
        "hash": "7bc91f2d00d89e7fda734556d0121946",
        "final_file": "lib/libcurl.so.4.8.0"
    },
    {
        # something with install_dir
        "name": "php-zts",
        "base_url": "https://packages.couchbase.com/couchbase-server/deps/php",
        "platform": "linux",
        "version": "8.0.2-cb1",
        "install_dir": "/tmp/php/php-zts-8.0.2-cb1",
        "filename": "php-zts-linux-x86_64-8.0.2-cb1.tgz",
        "hash": "fe52a6efd938d5d3ed4c5b9031477fe9",
        "final_file": "bin/php"
    },
    {
        # something with run
        "name": "docker",
        "platform": "linux",
        "version": "20.10.3",
        "filename": "docker-20.10.3.tgz",
        "hash": "4bb3ff2457b540995ddae3124f06d40a",
        "final_file": "bin/docker"
    },
    {
        # something with both toplevel_dir and create_toplevel_dir
        "name": "uv",
        "platform": "unknown-linux-gnu",
        "version": "0.4.29",
        "filename": "uv-x86_64-unknown-linux-gnu.tar.gz",
        "hash": "3c08a4629ca3368f80e26a091a6f1496",
        "final_file": "bin/uvx"
    }
]
config = "../../cbdep.config"

config = Path(config)
wd = Path(tempfile.mkdtemp())
logger = logging.getLogger()

def clear_wd():
    rmtree(wd, ignore_errors=True)

class TestInstaller:

    def test_fromYaml(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        assert type(installer) == Installer

    def test___del__(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        tempdir = Path(installer.temp_dir)
        tempdir.mkdir(exist_ok=True)
        assert tempdir.exists()
        del installer
        assert tempdir.exists() == False

    def test_copy(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        assert type(installer.copy()) == Installer

    def test_set_cache_only(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        installer.set_cache_only(False)
        assert installer.cache_only == False
        installer.set_cache_only(True)
        assert installer.cache_only == True

    def test_recache(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        installer.set_recache(False)
        assert installer.recache == False
        installer.set_recache(True)
        assert installer.recache == True

    def test_set_from_local_file(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        Path("/tmp/bar").touch()
        installer.set_recache(True)
        installer.set_from_local_file("/tmp/bar")
        assert installer.recache == False
        with pytest.raises(SystemExit) as e:
                installer.set_from_local_file("/tmp/barbaz")
        assert e.type == SystemExit
        assert e.value.code == 1

    def test_get_installer_file(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        installer.installer_file = "foo"
        assert installer.get_installer_file() == "foo"

    def test_templatize(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        installer.symbols["ALPHA"] = "ABC"
        installer.symbols["NUMERIC"] = "123"
        assert installer.templatize("${ALPHA}-${NUMERIC}") == "ABC-123"

    # Fixture to parameterize test_working_install() for each package config
    @pytest.fixture(params=install_packages, ids=package_name)
    def package(self, request):
        return request.param

    def test_working_install(self, caplog, package):
        caplog.set_level(logging.DEBUG)
        clear_wd()
        logger.info(f"Testing package '{package}'")
        installer = Installer.fromYaml(config, Cache(wd), package["platform"], package.get("arch", plat.get_arches()))
        installer.install(package["name"], package["version"], package.get("base_url", ""), wd/"install")
        fn = wd / package["hash"][0:2] / package["hash"] / package.get("filename", f"{package['name']}-{package['version']}.tar.gz")
        logger.debug(f"    Checking for downloaded file '{fn}'")
        assert fn.is_file()
        install_dir = Path(package.get("install_dir", f"{package['name']}-{package['version']}"))
        if not install_dir.is_absolute():
            install_dir = wd / "install" / install_dir
        logger.debug(f"    Checking for install dir '{install_dir}'")
        assert install_dir.is_dir()
        final_filename = package.get("final_file", None)
        if final_filename is not None:
            logger.debug(f"    Checking for final file '{final_filename}'")
            assert (install_dir / final_filename).is_file()
        rmtree(install_dir, ignore_errors=True)

    def test_broken_install(self):
        clear_wd()
        installer = Installer.fromYaml(config, Cache(wd), missing_package["platform"], "x86_64")
        with pytest.raises(SystemExit) as e:
                installer.install(missing_package["name"], missing_package["version"], missing_package.get("base_url", ""), wd/"install")
        assert e.type == SystemExit
        assert e.value.code == 1

    def test_wrong_platform_install(self):
        clear_wd()
        installer = Installer.fromYaml(config, Cache(wd), wrong_platform_package["platform"], "x86_64")
        with pytest.raises(SystemExit) as e:
            installer.install(wrong_platform_package["name"], wrong_platform_package["version"], wrong_platform_package.get("base_url", ""), wd/"install")
        assert e.type == SystemExit
        assert e.value.code == 1

    def test_handle_set_env(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        installer.symbols["foo"] = "bar"
        os.environ["test_handle_set_env"] = ""
        installer.handle_set_env({ "test_handle_set_env": "xxx" })
        assert os.environ["test_handle_set_env"] == "xxx"

    def test_handle_fixed_dir(self):
        rmtree(wd, ignore_errors=True)
        wd.mkdir()
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        installer.symbols["foo"] = "bar"
        installer.handle_fixed_dir({ "fixed_dir": str(wd/"missing") })
        assert installer.handle_fixed_dir({ "fixed_dir": str(wd/"missing") }) == False
        (wd/"present").touch()
        assert installer.handle_fixed_dir({ "fixed_dir": str(wd/"present") }) == True

    def test_do_install_dir(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        action = {
            "install_dir": str(wd / "test_do_install_dir")
        }
        installer.do_install_dir(action)
        assert installer.symbols["INSTALL_DIR"] == str(wd / "test_do_install_dir")

    def test_do_cbdep(self):
        rmtree(wd, ignore_errors=True)
        wd.mkdir()
        assert config
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        installer.do_cbdep({"cbdep": "analytics-jars", "version": "7.0.2-6512", "install_dir": str(wd/"test_do_cbdep")})
        assert md5(open(wd/"test_do_cbdep"/"analytics-jars-7.0.2-6512"/"cbas-install-7.0.2.jar", "rb").read()).hexdigest() == "3436fda4756c9aed996a6ad2ed9ddb30"
