import os
from setuptools import setup

setup(
    name = "torram",
    version = "0.9.0",
    install_requires = ['bencode'],
    scripts = ['torram'],

    # Metadata
    author = "Volodymyr Buell (Buiel)",
    author_email = "vbuell@gmail.com",
    url = "https://github.com/vbuell/torrent-upstart",
    description = ("Utility that recreats a torrent download folder with fully and partially downloaded files.")
#    license="APL2",
)