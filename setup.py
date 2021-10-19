from setuptools import setup, find_packages
import pathlib
import re

here = pathlib.Path(__file__).parent.resolve()
content = (here / 'README.md').read_text(encoding='utf-8')

summary = re.search('(?sia)What\?\n----\n(.+?)\n\n', content)[1]


setup(
    name='toraio',
    version='1.0.5',
    url='https://github.com/ultrafunkamsterdam/toraio',
    license='MIT',
    author='UltrafunkAmsterdam',
    author_email='',
    desc=summary,
    long_description=content,
    long_description_content_type='text/markdown',
    package_dir={'toraio': 'toraio'},
    packages=['toraio'],
    include_package_data=True,
    install_requires=[
        'socks',
        'aiohttp',
        'aiosocks2',
        'stem',
    ]

)