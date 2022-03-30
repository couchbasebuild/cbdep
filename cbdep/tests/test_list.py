import argparse
import pathlib
import pytest
import sys
sys.path.append('../scripts')
import main

class TestList:
    def test__list(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--config-file", type=str)
        args = parser.parse_args([
            "--config-file",
            str(pathlib.Path.cwd() / ".." / ".." / "cbdep.config")
        ])
        tool = main.Cbdep()
        tool.do_list(args)
