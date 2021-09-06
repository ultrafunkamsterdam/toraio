from setuptools import setup, find_packages

# data_files = []
# pth = pathlib.Path('aiotor/bin')
# for item in pth.rglob('*'):
#     if item.is_dir():
#         continue
#     data_files += [str(item.parent.relative_to(pth.parents[0])), str(item.relative_to(pth.parents[0]))]
#
#
# # data_files = [x[:-1] if x[-1] == os.sep else x for x in glob.glob('aiotor/bin/*', recursive=True)]
# for df in data_files:
#     print(df)
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
    # data_files={
    #     'aiotor': ['./aiotor/bin/*.*']
    # },
    install_requires=[
        'aiosocks',
        'socks',
        'aiohttp',
        'stem',
    ]

)