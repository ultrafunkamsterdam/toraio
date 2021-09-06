import glob
from distutils.core import setup

data_files = [x.replace('\\', '/') for x in glob.glob('aiotor/bin/**', recursive=True)]
setup(
    name='aiotor',
    version='3.0',
    url='https://github.com/ultrafunkamsterdam/aiotor',
    license='MIT',
    author='UltrafunkAmsterdam',
    author_email='',
    description='',
    packages=['aiotor'],
    include_package_data=True,

    install_requires=[
        'aiosocks',
        'socks',
        'aiohttp',
        'stem',
    ]

)