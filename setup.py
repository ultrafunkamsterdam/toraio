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
        uid, gid = 0, 0
        mode = 0o700
        install.run(self)
        # calling install.run(self) insures that everything that happened previously still happens, so the installation does not break!

        # here we start with doing our overriding and private magic ..
        for filepath in self.get_outputs():
            exepath = os.path.join('Tor', 'tor')
            if exepath in filepath:
                log.info('setting %s executable' % filepath)
                os.chmod(filepath, mode)

            # if self.install_scripts in filepath:
            #
            #
            #     log.info("Overriding setuptools mode of scripts ...")
            #     log.info("Changing ownership of %s to uid:%s gid %s" %
            #              (filepath, uid, gid))
            #     os.chown(filepath, uid, gid)
            #     log.info("Changing permissions of %s to %s" %
            #              (filepath, oct(mode)))
            #     os.chmod(filepath, mode)

setup(
    name='toraio',
    version='1.0.7',
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