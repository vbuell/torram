# torram

torram (former torrent-upstart) is a utility that recreates a torrent download
directory from fully and partially downloaded file(s). If several
partially-downloaded sources of the same incompleted torrent files found, it
merges them together.

## Use cases

There are two major cases when this utility will help you to save trafic or to
help recovering the files:

#### "hey, where are all seeders?" situation

That's the most common situation: you have several torrents having the same
file(s) but for some reason these torrents are dead, so you have 75% done for
one source and 85% done of another... there are chances that you actually have
enough information to combine downloaded blocks from incomplete file #1 with
downloaded blocks from file #2 to get a complete file as a result. The more
sources you have, the better result you'll get.

> :warning: After files are combined, do "Force check" in your torrent client.
> Otherwise the torrent client won't know that the files were changed.

**Note**: I had positive experience recovering some extra rare artifacts by
merging partially downloaded files obtained by different p2p sources: torrent
and mlDonkey temp directory. In that case just make sure that both files are
children of the *root* directory (see Usage section).

#### "I don't like to download it twice" situation

It's a good idea to scan your HDD drive with this utility before starting
downloading in terms of reusing already downloaded file.

> :warning: Again, make sure that you "Force check" torrent after you run this
> tool...

**Note**: Due to technical implementation of how files are being split into
chunks in .torrent, sometimes it's impossible to check md5 sum of first and last
chunk of the file. So after "Force check" is done you may see that file is 99%
complete even though it's actually 100%.

## How does it work

Each .torrent file consist of one or several files, each of them defined as a
record of fields: file name, file size, file's hash, plus an error detection
information in the form of md5 hash sum for all chunk. This error detection part
allows us to do the trick - find chunks with the same md5 sum from files in your
filesystem and generate output file using this chunks.

So the algorithm is:

 * scan *root* directory (last positional arg) recursively and find ponential
   pretenders for each file of .torrent file using to simple matching rules:
   file should be either named as required or should have the same file size
 * for each pretenders of .torrent file we do split pretender file into chunks
   and calculate md5 sum for every chunk in order to find blocks that we will
   use to put in destination file
 * if multiple pretenders found having reusable blocks then we prompts user to
   choose one of method: merge from multiple files (default); use one of files
   without merging; or skip the file
 * based of user's selection the tool will create a file (or skip creation) and
   place it in output directory (`-o` argument)


## Features

 * Combine several partially-downloaded sources into one (yes, it does work!)
 * Autodetect output directory (qBittorrent only for now)
 * Use symlinks instead of copying a file (danger... danger... danger...)
 * Manual and automatic modes (several levels of automation. See `-s`, `-ss`
   switches)
 
## Requirements

 * Python >= 2.6, but < 3.0 (porting to 3.0 is in progress)
 * bencode 1.0 (https://pypi.python.org/pypi/bencode)
 * PyQt4 (only if you use qBittorrent output directory autodetection, switch
   `--autodetect_output_dir`)

## Usage

```
> ./torram.py --help
usage: torram [-h] [--symlink] [--minsize MINSIZE] [-v] [-o OUTPUT_DIR] [-a]
              [-c] [-s] [--fileext FILE_EXT] [--version]
              torrentFile root

Recreate download directory for .torrent file from fully and partially
downloaded file(s).

positional arguments:
  torrentFile           .torrent file to analyze
  root                  Directory to recursively search files in

optional arguments:
  -h, --help            show this help message and exit
  --symlink             Use symlinks instead of copying files. (Caution: You
                        may lose your data if files actually are not
                        indentical.)
  --minsize MINSIZE     Minimum file size in bytes to be recoverable. Default:
                        1048576
  -v, --verbose         Be verbose (multiple levels: use -vv or -vvv to see
                        more)
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Output directory where to place recreated files
  -a, --autodetect_output_dir
                        Autodetect output directory (only qBittorrent
                        currently supported)
  -c, --use_color       Output format: [ansi, ascii]
  -s, --autoskip        Dont ask questions if there is only one viable choise.
                        Use -ss to behave even more automated
  --fileext FILE_EXT    Extension to be added to output files (ex, .!qB for
                        incomplete qBittorrent files)
  --version             show program's version number and exit
```