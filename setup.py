import os
from setuptools import setup

setup(
    name = "torram",
    version = "1.0.1",
    install_requires = ['bencode.py'],
    scripts = ['torram'],

    # Metadata
    author = "Volodymyr Buell (Buiel)",
    author_email = "vbuell@gmail.com",
    url = "https://github.com/vbuell/torrent-upstart",
    description = ("Utility that recreats a torrent download folder with fully and partially downloaded files.")
#    license="APL2",
)