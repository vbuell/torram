#!/usr/bin/python
import sys
import os
import hashlib
import StringIO
import bencode
import re
import shutil
import tempfile
import stat


DELUGE_DIR = '~/.config/deluge/state'
QBITTORRENT_RESUME_CONF = '~/.config/qBittorrent/qBittorrent-resume.conf'
FILES_DIR = '~'
MINIMUM_FILESIZE_TO_SEARCH = 1024 * 1024


class AnsiFormatter(object):
    aaa = {'RED': "\033[31m",
           'BOLD': "\033[1m",
           'YELLOW': "\033[33m",
           'INVERT': "\033[40m\033[37m",
           'GREEN': "\033[32m",
           'BLUE': "\033[34m",
           'BLACK2': "\033[90m",
           'BLACK1': "\033[37m",
           'BLACK0': "\033[97m",
           }

    def format(self, txt, *code):
        return ''.join([self.aaa[c] for c in code]) + txt + "\033[0m"


class BaseFormatter(object):
    def format(self, txt, *code):
        return txt


class FileInfo():
    def __init__(self):
        self.start_offset = None
        self.isOriginal = False
        self.isHardlink = False


def suggest_method(file_infos):
    fullest_file_idx = None
    fullest_file_rate = 0
    downladed_file_rate = 0
    mixed_pieces = []

    # calculate per file
    for idx, file_info in enumerate(file_infos):
        if len(file_info.chunks) == 0:
            return 'S'
        num_of_success = file_info.num_of_good_chunks
        rate = float(num_of_success) / len(file_info.chunks)
        if file_info.isOriginal:
            downladed_file_rate = rate
        if rate > fullest_file_rate:
            fullest_file_rate = rate
            fullest_file_idx = idx

    # calculate mixed
    if len(file_infos) > 1:
        for aa in zip(*[fi.chunks for fi in file_infos]):
    #        print aa, type(aa), any(aa)
            mixed_pieces.append(any(aa))
        num_of_success = reduce(lambda x, y: x + int(y), mixed_pieces, 0)

        if float(num_of_success) / len(mixed_pieces) > fullest_file_rate:
            pattern = 'Got [{0} of {1} good pieces from {2} files.'
            print fmt.format(pattern.format(num_of_success, len(mixed_pieces), len(file_infos)), 'RED', 'BOLD')
            return 'M'

    if downladed_file_rate >= fullest_file_rate:
        return 'S'
    return str(fullest_file_idx)


def get_similatity_rate_and_color(success_blocks, all_blocks):
    if all_blocks == 0:
        return 'BLACK2', 'Bad'

    rate = float(success_blocks) / all_blocks
    if rate > 0.9:
        return 'GREEN', 'Excellent'
    if rate > 0.5:
        return 'YELLOW', 'Good'
    if rate > 0.01:
        return 'YELLOW', 'Poor'
    else:
        return 'BLACK2', 'Bad'


def get_file_sizes(info):
    global args
    if 'files' in info:     # yield pieces from a multi-file torrent
        return [fi['length'] for fi in info['files'] if fi['length'] > int(args.minsize)]
    else:       # yield pieces from a single file torrent
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


def remove_hard_links(files):
    inode_to_filename = {}
    for filename in files:
        stat_info = os.stat(filename)
        inode_to_filename[stat_info[stat.ST_INO]] = filename
    return inode_to_filename.values()


def load_qbittorrent_conf(hash):
    """Load qBittorrent settings."""
    from PyQt4 import QtCore

    settings = QtCore.QSettings(os.path.expanduser(QBITTORRENT_RESUME_CONF), QtCore.QSettings.IniFormat)

    root = settings.value('torrents').toPyObject()
    record = root[QtCore.QString(hash)]
    path = record[QtCore.QString('save_path')]

    if isinstance(path, QtCore.QString):
        path = str(path)

    return path


def check_file_chunk(hash, offset, length, file):
    with open(file.decode('UTF-8'), "rb") as sfile:
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


def construct_file(file_infos, piece_length, dest_filename):
    # TODO: Get biggest file
    max_num_of_good_chunks = max(fi.num_of_good_chunks for fi in file_infos)
    biggest_file = next(fi for fi in file_infos if fi.num_of_good_chunks == max_num_of_good_chunks)

    f = tempfile.NamedTemporaryFile(mode='w+b', delete=False)
    file_name = f.name
    print "Temporary file:", file_name
    f.close()
    print "Copy file: ", biggest_file.path
    shutil.copy(biggest_file.path, f.name)

    if len(file_infos) > 1:
        with open(file_name, 'r+b') as f:
            for chunk_idx, chunks_merged in enumerate(zip(*[fi.chunks for fi in file_infos])):
                for i, p in enumerate(chunks_merged):
                    if p:
                        # copy chunk from and to (file_offset, piece_length)
                        file_info = file_infos[i]
                        src = open(file_info.path, 'rb')
                        src.seek(file_info.start_offset + chunk_idx * piece_length)
                        f.seek(file_info.start_offset + chunk_idx * piece_length)
                        f.write(src.read(piece_length))
                        src.close()
                        break

    print "Move temporary file to ", dest_filename
    shutil.move(file_name, dest_filename)


def ensure_dir_exists(f):
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
    destination_path = os.path.join(save_path, basedir, file_name)

    if file_length in files:
        print "Processing file: " + fmt.format(str(file_name), 'BLUE', 'BOLD')
        file_infos = []

        add_incomplete_file_with_different_size(destination_path, files[file_length])

        if args.autoskip and len(files[file_length]) < 2 and \
                max(file.startswith(destination_path) for file in files[file_length]):
            print "Only one file found. Thus, skipping..."
            return

        uniq_filenames = remove_hard_links(files[file_length])

        for file_number, file in enumerate(files[file_length]):
            file_info = FileInfo()
            file_info.path = file

            if file.startswith(destination_path):
                number_to_show = ' * '
                file_info.isOriginal = True
            else:
                number_to_show = ' ' + str(file_number) + ' '
            if file in uniq_filenames:
                pieces.seek(0)
                sys.stdout.write(fmt.format(number_to_show, 'BLACK0', 'BOLD') + str(file))

                num_of_checks = 0
                num_of_successes = 0
                offset = 0
                pieces_list = []
                while True:
                    hash = pieces.read(20)
                    if not hash:
                        break
                    idx, file_offset = get_chunk(files_sizes_array, offset * piece_length)
                    if not file_info.start_offset:
                        file_info.start_offset = file_offset

                    if idx == file_idx:
                        num_of_checks += 1
                        hash_result = check_file_chunk(hash, file_offset, piece_length, file)
                        pieces_list.append(hash_result)
                        if hash_result:
                            num_of_successes += 1

                    offset += 1

                file_info.chunks = pieces_list
                file_info.num_of_good_chunks = num_of_successes
                file_infos.append(file_info)

                color_code, result_message = get_similatity_rate_and_color(num_of_successes, num_of_checks)
                pattern = ' [{0} of {1}] ({2})'
                print(fmt.format(pattern.format(num_of_successes, num_of_checks, result_message), color_code))
            else:
                sys.stdout.write(fmt.format(number_to_show, 'BLACK0', 'BOLD') + str(file) + " hardlink -> skipped\n")

        suggestion = suggest_method(file_infos)
        while True:
            input = ''
            if args.autoskip < 2 and not (suggestion == 'S' and args.autoskip > 0):
                input = raw_input(fmt.format('Choose file number or S/M/A [<N>/S/M/A] ({0}) '.format(suggestion), 'INVERT'))

            if input == '':
                input = suggestion
            if re.match('^[0-9]+$', input):
                src_path = files[file_length][int(input)]
                print 'Copying:', destination_path, src_path
                ensure_dir_exists(destination_path)
                shutil.copyfile(src_path, destination_path + '.!qB')
                break
            elif input.upper() == 'M':
                print('Creating mixed file from multiple sources')
                ensure_dir_exists(destination_path)
                construct_file(file_infos, piece_length, destination_path + '.!qB')
                break
            elif input.upper() == 'S':
                print('Skipping...')
                break
            elif input.upper() == 'A':
                print('Autoselect default option')
                args.autoskip = 2
            else:
                print('Mmmm?')

    else:
        if args.verbose > 0:
            print "Skipping file:", file_name


def add_incomplete_file_with_different_size(filepath, list):
    try:
        for filename in os.listdir(os.path.dirname(filepath)):
            curr_filepath = os.path.join(os.path.dirname(filepath), filename)
            if curr_filepath.startswith(filepath):
                if curr_filepath not in list:
                    list.append(curr_filepath)
    except OSError, ex:
        print ex


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
                        help='Use symlinks instead of copying files. '
                             '(Caution: You may lost data if files actually are not the same.)')
    parser.add_argument('--minsize', default=MINIMUM_FILESIZE_TO_SEARCH)
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('-o', '--output_dir', dest='output_dir',
                        help='Output directory where to create new download directory')
    parser.add_argument('-a', '--autodetect_output_dir', dest='autodetect_output_dir', action='store_true',
                        help='Autodetect output directory using config directory of torrent clients '
                             '(qBittorrent currently supported only)')
    parser.add_argument('-c', '--use_color', dest='use_color', action='store_true', help='Output format: [ansi, ascii]')
    parser.add_argument('-s', '--autoskip', dest='autoskip', action='count', default=0,
                        help='Auto-skip when there in no choise')
    args = parser.parse_args()

    if args.use_color:
        fmt = AnsiFormatter()
    else:
        fmt = BaseFormatter()

    main()
