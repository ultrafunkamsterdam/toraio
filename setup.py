from setuptools import setup
from setuptools.command.install import install
from setuptools.command.install_scripts import install_scripts
import pathlib
import re
import os


here = pathlib.Path(__file__).parent.resolve()
content = (here / 'README.md').read_text(encoding='utf-8')

summary = re.search('(?sia)What\?\n----\n(.+?)\n\n', content)[1]




setup(
    name='toraio',
    version='1.0.6',
    url='https://github.com/ultrafunkamsterdam/toraio',
    license='MIT',
    author='UltrafunkAmsterdam',
    author_email='',
    desc=summary,
    long_description=content,
    long_description_content_type='text/markdown',
    package_dir={'toraio': 'toraio'},
    package_data={'toraio': ['bin/linux/Tor/tor', 'bin/linux/*' ,'bin/win32/Tor/tor.exe']
                  },
    packages=['toraio'],
    include_package_data=True,
    install_requires=[
        'socks',
        'aiohttp',
        'aiosocks2',
        'stem',
    ],


)