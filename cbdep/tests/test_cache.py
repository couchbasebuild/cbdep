import pytest
import requests
import sys
import tempfile
from hashlib import md5
from pathlib import Path
from shutil import rmtree
from urllib.parse import urljoin
sys.path.append('../scripts')
from cache import Cache

dep_url_path = "https://packages.couchbase.com/couchbase-server/deps/openssl/1.1.1l/1/"

filename = {
    "centos": "openssl-centos7-x86_64-1.1.1l-1.tgz",
    "ubuntu": "openssl-ubuntu20.04-x86_64-1.1.1l-1.tgz"
}
url = {
    "centos": urljoin(dep_url_path, filename["centos"]),
    "ubuntu": urljoin(dep_url_path, filename["ubuntu"])
}
hash = {
    "centos": "d8ba3ac17a080a9cde889fdb26308bb8",
    "ubuntu": "59bfb1a1f49ab9e04e9993b3f0bcdc23"
}
name_sha = {
    "centos": md5(url["centos"].encode('utf-8')).hexdigest(),
    "ubuntu": md5(url["ubuntu"].encode('utf-8')).hexdigest()
}

cachedir = Path(tempfile.mkdtemp())

class TestCache:
    cache = Cache(cachedir)

    def test__cachefilename(self):
         assert self.cache._cachefilename(cachedir) == cachedir/"filename"

    def test__cachedir(self):
        rmtree(cachedir/name_sha["centos"][0:2], ignore_errors=True)
        path = cachedir/name_sha["centos"][0:2]/name_sha["centos"]
        urlfile = path / "url"
        assert self.cache._cachedir(url["centos"]) == path
        assert open(urlfile).read() == url["centos"]

    def test__writefilename(self):
        self.cache._writefilename(cachedir, "foo")
        assert open(cachedir/"filename").read() == "foo"
        self.cache._writefilename(cachedir, "bar")
        assert open(cachedir/"filename").read() == "bar"

    def test_save(self):
        self.cache.save(url["centos"], cachedir/"dummy")
        assert md5(open(cachedir/"dummy", "rb").read()).hexdigest() == hash["centos"]

    def test_report(self):
        from contextlib import redirect_stdout
        from io import StringIO
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.cache.report(url["centos"])
        assert stdout.getvalue().strip() == str(cachedir/name_sha["centos"][0:2]/name_sha["centos"]/url["centos"].split("/")[-1])

    def test_put(self):
        rmtree(cachedir, ignore_errors=True)
        cachedir.mkdir()
        r = requests.get(url["ubuntu"])
        with open(cachedir/"openssl-ubuntu20.04-x86_64-1.1.1l-1.tgz", 'wb') as f:
            f.write(r.content)
        self.cache.put(url["centos"], cachedir/"openssl-ubuntu20.04-x86_64-1.1.1l-1.tgz")
        assert open(cachedir/name_sha["centos"][0:2]/name_sha["centos"]/"filename").read() == filename["ubuntu"]
        assert open(cachedir/name_sha["centos"][0:2]/name_sha["centos"]/"url").read() == url["centos"]

    def test_get(self):
        rmtree(cachedir, ignore_errors=True)
        cachedir.mkdir()
        self.cache.get(url["ubuntu"])
        assert md5(open(cachedir/name_sha["ubuntu"][0:2]/name_sha["ubuntu"]/filename["ubuntu"], "rb").read()).hexdigest() == hash["ubuntu"]
        self.cache.get(url["ubuntu"])
        assert md5(open(cachedir/name_sha["ubuntu"][0:2]/name_sha["ubuntu"]/filename["ubuntu"], "rb").read()).hexdigest() == hash["ubuntu"]
        self.cache.get(url["ubuntu"], recache=True)
        assert md5(open(cachedir/name_sha["ubuntu"][0:2]/name_sha["ubuntu"]/filename["ubuntu"], "rb").read()).hexdigest() == hash["ubuntu"]
