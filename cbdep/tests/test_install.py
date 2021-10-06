import os
import sys
import pytest
from hashlib import md5
from pathlib import PosixPath
from shutil import rmtree
sys.path.append('../scripts')
from cbdep.cbdep.scripts.cache import Cache
from cbdep.cbdep.scripts.install import Installer

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

install_packages = [
    {
        "name": "dotnet-core-runtime",
        "platform": "linux",
        "version": "5.0.10",
        "filename": "dotnet-runtime-5.0.10-linux-x64.tar.gz",
        "hash": "ccd32f9a26d3f3d019ed00b9d0887efc",
    },
    {
        "name": "golang",
        "platform": "linux",
        "arch": "amd64",
        "version": "1.10.3",
        "filename": "go1.10.3.linux-amd64.tar.gz",
        "install_dir": "go1.10.3",
        "hash": "507f89d7c1f362709111f3a5d4f2d39c",
    },
    {
        # random cbddep
        "name": "analytics-jars",
        "base_url": "https://packages.couchbase.com/releases",
        "platform": "linux",
        "version": "7.0.2-6512",
        "hash": "0bbb2376f42848451b6898247aa85793",
    },
    {
        # java with its special cases
        "name": "java",
        "platform": "linux",
        "version": "11.0.3",
        "filename": "jdk-11.0.3_linux-x64_bin.tar.gz",
        "hash": "9bdefa0ac6378798643934ea6a065fe1"
    },
    {
        "name": "java",
        "platform": "linux",
        "version": "8u181",
        "filename": "jdk-8u181-linux-x64.tar.gz",
        "hash": "fb5902b789ef52fbb5852b909b6f19b7"
    },
    {
        # classic cbdep
        "name": "boost",
        "base_url": "https://packages.couchbase.com/couchbase-server/deps",
        "platform": "centos7",
        "version": "1.74.0-cb1",
        "filename": "boost-centos7-x86_64-1.74.0-cb1.tgz",
        "hash": "74e40ef0dddb0be854b91054c4120706"
    },
    {
        # something with install_dir
        "name": "php-zts",
        "base_url": "https://packages.couchbase.com/couchbase-server/deps/php",
        "platform": "linux",
        "version": "8.0.2-cb1",
        "install_dir": "/tmp/php/php-zts-8.0.2-cb1",
        "filename": "php-zts-linux-x86_64-8.0.2-cb1.tgz",
        "hash": "fe52a6efd938d5d3ed4c5b9031477fe9"
    },
    {
        # something with run
        "name": "jq",
        "platform": "linux",
        "version": "1.6",
        "filename": "jq-linux64",
        "hash": "5f30d82f019df2c03e074cbb1551533d"
    }
]
config = "../../cbdep.config"

config = PosixPath(config)
wd = PosixPath("/tmp/cbdep-testing")

def clear_wd():
    rmtree(wd, ignore_errors=True)

class TestInstaller:

    def test_fromYaml(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        assert type(installer) == Installer

    def test___del__(self):
        installer = Installer.fromYaml(config, Cache(wd), "linux", "x86_64")
        tempdir = PosixPath(installer.temp_dir)
        if not os.path.exists(tempdir):
            tempdir.mkdir()
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
        PosixPath("/tmp/bar").touch()
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

    def test_working_install(self):
        clear_wd()
        assert len(install_packages) > 0
        for package in install_packages:
            installer = Installer.fromYaml(config, Cache(wd), package["platform"], package.get("arch", "x86_64"))
            installer.install(package["name"], package["version"], package.get("base_url", ""), wd/"install")
            fn = wd / package["hash"][0:2] / package["hash"] / package.get("filename", f"{package['name']}-{package['version']}.tar.gz")
            assert os.path.isfile(fn)
            install_dir = package.get("install_dir", f"{package['name']}-{package['version']}")
            if not os.path.isabs(install_dir):
                install_dir = wd / "install" / install_dir
            assert os.path.isdir(install_dir)
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
        PosixPath(wd/"present").touch()
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
