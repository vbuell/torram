# torrent-upstart

torrent-upstart is a utility for filling a torrent download filder with the alreday downloaded files.

## Features

 * Mix several partially-downloaded sources into one (yes. And it does work!)
 * Ability to specify directory to search for files
 * Autodetect output directory (qBittorrent only for now)
 * Using symlinks instead of copying a file
 * Manual and automatic mode (see -s, -ss params)
 
## Requirements

 * Python >= 2.6, but < 3.0 (porting to 3.0 is in progress)
 * bencode (https://pypi.python.org/pypi/bencode)

## Usage

```
 % ./torram.py --help
usage: torram.py [-h] [--symlink] [--minsize MINSIZE] [--verbose]
                 [-o OUTPUT_DIR] [-a] [-c] [-s]
                 torrentFile root

Tries to find files used in torrent and generate download folder using them.

positional arguments:
  torrentFile           File to analyze
  root                  Dir to search

optional arguments:
  -h, --help            show this help message and exit
  --symlink             Use symlinks instead of copying files. (Caution: You
                        may lost data if files actually are not the same.)
  --minsize MINSIZE
  --verbose, -v
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Output directory where to create new download
                        directory
  -a, --autodetect_output_dir
                        Autodetect output directory using config directory of
                        torrent clients (qBittorrent currently supported only)
  -c, --use_color       Output format: [ansi, ascii]
  -s, --autoskip        Auto-skip when there in no choise
```