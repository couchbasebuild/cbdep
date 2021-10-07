import pytest
import cbdep.cbdep.scripts.platform_introspection as plat

class TestPlatformIntrospection:

    @pytest.fixture(autouse=True)
    def cleanup(self):
        yield
        plat._processor = None
        plat._platforms = None

    def test__override_arch(self):
        plat.override_arch("arm64")
        assert plat.get_arches() == ["aarch64", "arm64"]
