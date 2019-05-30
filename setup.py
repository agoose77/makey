from setuptools import setup

setup(
    name='makey',
    version='0.0.3',
    packages=['makey'],
    url='https://github.com/agoose77/makey',
    license='MIT',
    author='Angus Hollands',
    author_email='goosey15@gmail.com',
    description='Make libraries from GIT/url/tarball with CMAKE, and install using checkinstall.',
    entry_points={
        'console_scripts': [
            'makey = makey.__main__:main'
        ]
    }
)
