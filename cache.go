package cbdep

import (
	"crypto/md5"
	"fmt"
	"os"
	"path"
	"path/filepath"

	getter "github.com/hashicorp/go-getter"
)

var (
	cacheDir = filepath.Join(os.Getenv("HOME"), ".cbdepcache")
)

type CacheEntry struct {
	Url      string
	Filename string
}

func getFilename(url string) string {
	md5 := fmt.Sprintf("%x", md5.Sum([]byte(url)))

	return filepath.Join(cacheDir, md5[0:2], md5, path.Base(url))
}

func Cache(url string) (*CacheEntry, error) {
	filename := getFilename(url)
	newEntry := &CacheEntry{
		Url:      url,
		Filename: filename,
	}

	// If it already exists, we're done
	if _, err := os.Stat(filename); !os.IsNotExist(err) {
		fmt.Println("Already exists!")
		return newEntry, nil
	}

	fmt.Printf("Caching %s...\n", url)

	client := &getter.Client{
		Src:  url + "?archive=false",
		Dst:  filename,
		Mode: getter.ClientModeFile,
	}

	if err := client.Get(); err != nil {
		// Remove partial downloads; don't care if it doesn't exist
		os.Remove(filename)
		return nil, err
	}

	return newEntry, nil
}
