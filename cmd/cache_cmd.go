package cmd

import (
	"log"
	"os"

	"github.com/couchbase/cbdep"

	cli "github.com/jawher/mow.cli"
)

func init() {
	RootApp.Command("cache", "Add downloaded URL to local cache", func(cmd *cli.Cmd) {
		url := cmd.StringArg("URL", "", "URL to cache")
		cmd.Action = func() {
			if _, err := cbdep.Cache(*url); err != nil {
				log.Fatal("Error caching ", *url, ": ", err)
				os.Exit(1)
			}
		}
	})
}
