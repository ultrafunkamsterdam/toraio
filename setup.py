from setuptools import setup
from setuptools.command.install import install
from setuptools.command.install_scripts import install_scripts
from distutils import log
import pathlib
import re
import os


here = pathlib.Path(__file__).parent.resolve()
content = (here / 'README.md').read_text(encoding='utf-8')

summary = re.search('(?sia)What\?\n----\n(.+?)\n\n', content)[1]





class postinstall(install):
    """Post-installation for development mode."""
    def run(self):
        mode = 0o700
        install.run(self)
        for filepath in self.get_outputs():
            exepath = os.path.join('Tor', 'tor')
            if exepath in filepath:
                log.warn('setting %s executable' % filepath)
                os.chmod(filepath, mode)

setup(
    name='toraio',
    version='1.0.9',
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

    cmdclass = {
               'install': postinstall,
           },

)
