#!/usr/bin/python
import sys, os, hashlib, StringIO, bencode, re, shutil, tempfile


DELUGE_DIR = '~/.config/deluge/state'
FILES_DIR = '~'
MINIMUM_FILESIZE_TO_SEARCH = 1024 * 1024
DO_NOT_SHOW_SKIPPED = True

class AnsiFormatter(object):
    aaa = {'RED': "\033[31m",
           'REDBOLD': "\033[31m\033[1m",
           'YELLOW': "\033[33m",
           'INVERT': "\033[40m\033[37m",
           'GREEN': "\033[32m",
           'BLUEBOLD': "\033[34m\033[1m",
           'BLACK2': "\033[90m",
           'BLACK1': "\033[37m",
           'BLACK0': "\033[97m",
           'BLACK0BOLD': "\033[97m\033[1m"
    }

    def format(self, txt, code):
        return self.aaa[code] + txt + "\033[0m"


class BaseFormatter(object):
    def format(self, txt, code):
        return txt

def suggest_method(pieces, downladed_file_index):
    fullest_file_idx = None
    fullest_file_rate = 0
    downladed_file_rate = 0
    mixed_file_rate = 0
    mixed_pieces = []

    # calculate per file
    for idx, blocks in pieces.items():
        if len(blocks) == 0:
            return 'S'
        num_of_success = reduce(lambda x, y: x+int(y), blocks, 0)
        rate = float(num_of_success) / len(blocks)
        if idx == downladed_file_index:
            downladed_file_rate = rate
        if rate > fullest_file_rate:
            fullest_file_rate = rate
            fullest_file_idx = idx

    # calculate mixed
    if len(pieces) > 1:
        for aa in zip(*pieces.values()):
    #        print aa, type(aa), any(aa)
            mixed_pieces.append(any(aa))
        num_of_success = reduce(lambda x, y: x+int(y), mixed_pieces, 0)
        print "Got [" + str(num_of_success) + ' of ' + str(len(mixed_pieces)) + ' good pieces from ', len(pieces), 'files', float(num_of_success) / len(mixed_pieces)

        if float(num_of_success) / len(mixed_pieces) > fullest_file_rate:
            print fmt.format('Yeppee!!!!!', 'REDBOLD')
            return 'M'

    if downladed_file_rate >= fullest_file_rate:
        return 'S'
    return str(fullest_file_idx)


def get_similatity_rate_and_color(success_blocks, all_blocks):
    if all_blocks == 0:
        return ('BLACK2', 'Bad')

    rate = float(success_blocks) / all_blocks
    if rate > 0.9:
        return ('GREEN', 'Excelent')
    if rate > 0.5:
        return ('YELLOW', 'Good')
    if rate > 0.01:
        return ('YELLOW', 'Poor')
    else:
        return ('BLACK2', 'Bad')



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


def construct_file(chunks_data, files, pieces, file_idx):
    import tempfile, shutil

    # TODO: Get biggest file
    f = tempfile.NamedTemporaryFile(mode = 'w+b', delete=False)

    f.write('foo')
    file_name = f.name
    f.close()
    shutil.copy(files[0], f.name)

    f = open(f.name, 'w+b')

    chunk_idx = 0
    while True:
        hash = pieces.read(20)
        if not hash:
            break
        idx, file_offset = get_chunk(files_sizes_array, offset * piece_length)

        if idx == file_idx:

            for p in chunks_data:
                if p[chunk_idx] == True:
                    # copy chunk from and to (file_offset, piece_length)
                    filename = files[file_idx]
                    src = open(filename)
                    src.seek(file_offset)
                    f.seek(file_offset)
                    f.write(src.read(piece_length))
                    src.close()
                    break

            chunk_idx += 1

        offset += 1


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
        print "Processing file: " + fmt.format(str(file_name), 'BLUEBOLD')
        chunks_data = {}
        downladed_file_index = None

        add_incomplete_file_with_different_size(dest_path, files[file_length])

        for file_number, file in enumerate(files[file_length]):
            pieces.seek(0)
            if file.startswith(dest_path):
                number_to_show = ' * '
                downladed_file_index = file_number
            else:
                number_to_show = ' '+str(file_number)+' '
            sys.stdout.write(fmt.format(number_to_show, 'BLACK0BOLD') + str(file))

            num_of_checks = 0
            num_of_successes = 0
            offset = 0
            pieces_list = []
            while True:
                hash = pieces.read(20)
                if not hash:
                    break
                idx, file_offset = get_chunk(files_sizes_array, offset * piece_length)

                if idx == file_idx:
                    num_of_checks += 1
                    hash_result = check_file_chunk(hash, file_offset, piece_length, file)
                    pieces_list.append(hash_result)
                    if hash_result:
                        num_of_successes += 1

                offset += 1

            chunks_data[file_number] = pieces_list

            color_code, result_message = get_similatity_rate_and_color(num_of_successes, num_of_checks)
            print fmt.format(' [' + str(num_of_successes) + " of " + str(num_of_checks) + '] (' + result_message + ')', color_code)
        suggestion = suggest_method(chunks_data, downladed_file_index)
        input = raw_input(fmt.format('[<N>,S,M], default=' + suggestion + ':', 'INVERT'))
        if input == '':
            input = suggestion
        if re.match('^[0-9]+$', input):
            src_path = files[file_length][int(input)]
            print '#### copying:', dest_path, src_path
            ensure_dir(dest_path)
            shutil.copyfile(src_path, dest_path + '.!qB')
        else input == 'M':
            print 'create mixed file'
            construct_file(chunks_data, files[file_length], pieces, file_idx)


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
        help='Use symlinks instead of copying files. (Caution: You may lost data if files actually are not the same.)')
    parser.add_argument('--minsize', default=MINIMUM_FILESIZE_TO_SEARCH)
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('-o', '--output_dir', dest='output_dir', help='Output directory where to create new download directory')
    parser.add_argument('-a', '--autodetect_output_dir', dest='autodetect_output_dir', action='store_true',
        help='Autodetect output directory using config directory of torrent clients (Deluge currently supported only)')
    parser.add_argument('-c', '--use_color', dest='use_color', action='store_true', help='output_format [ansi, ascii]')
    args = parser.parse_args()

    if args.use_color:
        fmt = AnsiFormatter()
    else:
        fmt = BaseFormatter()

    main()
