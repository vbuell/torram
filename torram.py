#!/usr/bin/python
import sys, os, hashlib, StringIO, bencode, re, shutil


DELUGE_DIR = '~/.config/deluge/state'
FILES_DIR = '~'
MINIMUM_FILESIZE_TO_SEARCH = 1024 * 256
DO_NOT_SHOW_SKIPPED = True


def get_file_sizes(info):
    global args
    if 'files' in info: # yield pieces from a multi-file torrent
        return [fi['length'] for fi in info['files'] if fi['length'] > int(args.minsize)]
    else: # yield pieces from a single file torrent
        return [info['length']]


def get_possible_files(rootdir, sizes):
    """Find duplicate files in directory tree."""
    filesizes = {}
    # Build up dict with key as filesize and value is list of filenames.
    for path, dirs, files in os.walk(rootdir):
        for filename in files:
            filepath = os.path.join(path, filename)
            filesize = os.lstat(filepath).st_size
            if filesize in sizes:
                filesizes.setdefault(filesize, []).append(filepath)
    return filesizes


def load_qbittorrent_conf(hash):
    from PyQt4 import QtCore

    settings = QtCore.QSettings("/home/vbuell/.config/qBittorrent/qBittorrent-resume.conf", QtCore.QSettings.IniFormat)

    root = settings.value('torrents').toPyObject()
    record = root[QtCore.QString(hash)]
    path = record[QtCore.QString('save_path')]

    if (isinstance(path, QtCore.QString)):
        path = str(path)

    return path


def check_file_chunk(hash, offset, length, file):
    sfile = open(file.decode('UTF-8'), "rb")

    sfile.seek(offset)
    piece = sfile.read(length)

    piece_hash = hashlib.sha1(piece).digest()
    return piece_hash == hash


def get_chunk(filesizes, global_offset):
    """
    Returns file offset using global continuous file

    >>> get_chunk([], 0)
    (0, 0)
    >>> get_chunk([100], 0)
    (0, 0)
    >>> get_chunk([100], 100)
    (0, 0)
    >>> get_chunk([50,50,30], 100)
    (2, 0)
    """
    file_offset = 0
    file_idx = 0

    # Find file idx
    for filesize in filesizes:
        if file_offset + filesize > global_offset:
            break

        file_offset += filesize
        file_idx += 1

    return (file_idx, global_offset - file_offset)


def get_similatity_rate(success_blocks, all_blocks):
    if all_blocks == 0:
        return 0
    rate = success_blocks / all_blocks
    if rate > 0.9: return

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

def guess_file(file_info, file_idx, files, pieces, piece_length, files_sizes_array, basedir):
    global args
    global fmt
    global save_path

    if 'path' in file_info:
        file_name = os.path.join(*file_info['path'])
    else:
        file_name = file_info['name']

    file_length = file_info['length']
    dest_path = os.path.join(save_path, basedir, file_name)

    if file_length in files:
        print "Processing file:", file_name
        for idx, file in enumerate(files[file_length]):
            pieces.seek(0)
            if file == dest_path:
                sys.stdout.write(" * " + str(file))
            else:
                sys.stdout.write(" " + str(idx) + " " + str(file))

            num_of_checks = 0
            num_of_successes = 0
            offset = 0
            while True:
                hash = pieces.read(20)
                if not hash:
                    break
                idx, file_offset = get_chunk(files_sizes_array, offset * piece_length)

                if idx == file_idx:
                    num_of_checks += 1
                    if check_file_chunk(hash, file_offset, piece_length, file):
                        num_of_successes += 1

                offset += 1

            print "\t[", num_of_successes, "of", num_of_checks, ']'
        input = raw_input('[<N>,S]')
        if re.match('^[0-9]+$', input):
            src_path = files[file_length][int(input)]
            print '#### create symlink:', dest_path, src_path
            ensure_dir(dest_path)
            shutil.copyfile(src_path, dest_path + '.!qB')

    else:
        if args.verbose > 0:
            print "Skipping file:", file_name


def main():
    global args
    global save_path

    # Open torrent file
    torrent_file = open(args.torrentfile, "rb")
    metainfo = bencode.bdecode(torrent_file.read())
    info = metainfo['info']
    pieces = StringIO.StringIO(info['pieces'])

    hash = hashlib.sha1(bencode.bencode(info)).hexdigest()
    print "Hash:", hash

    sizes = get_file_sizes(info)
    print 'Sizes', sizes

    if args.autodetect_output_dir:
        save_path = load_qbittorrent_conf(hash)
        print save_path

    # Get possible files
    print 'Searching for file pretenders...'
    files = get_possible_files(os.path.expanduser(args.root), sizes)

    # Check files one by one
    if 'files' in info:
        files_sizes_array = [f['length'] for f in info['files']]
        file_idx = 0
        for f in info['files']:
            guess_file(f, file_idx, files, pieces, info['piece length'], files_sizes_array, info['name'])
            file_idx += 1
    else:
        print info.keys()
        files_sizes_array = [info['length']]
        guess_file(info, 0, files, pieces, info['piece length'], files_sizes_array, '')


if __name__ == "__main__":
#    import doctest
#    doctest.testmod()

    from argparse import ArgumentParser

    parser = ArgumentParser(description='Tries to find files used in torrent and generate download folder using them.')
    parser.add_argument('torrentfile', metavar='torrentFile', help='File to analyze')
    parser.add_argument('root', metavar='root', help='Dir to search')
    parser.add_argument('--symlink', action='store_true',
        help='Use symlinks instead of copying files. (Caution: You may lost data if files actually are not the same.)')
    parser.add_argument('--minsize', default=MINIMUM_FILESIZE_TO_SEARCH)
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('-o', '--output_dir', dest='output_dir', help='Output directory where to create new download directory')
    parser.add_argument('-a', '--autodetect_output_dir', dest='autodetect_output_dir', action='store_true',
        help='Autodetect output directory using config directory of torrent clients (Deluge currently supported only)')

#    parser.add_argument('-o', '--output_format', dest='output_format', help='output_format [ansi, ascii]',
#        default="ansi")
    args = parser.parse_args()

#    if args.output_format == 'ansi':
#        fmt = AnsiFormatter()
#    else:
#        fmt = BaseFormatter()

    main()
