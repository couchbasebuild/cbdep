import argparse
import cbdep.cli as cli

class TestList:
    def test__list(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--config-file", type=str)
        args = parser.parse_args()
        tool = cli.Cbdep()
        tool.do_list(args)
