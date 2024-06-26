from setuptools import setup, find_packages

setup(
    name='efl',
    version='0.1.0',
    packages=find_packages(include=['efl', 'efl.*']),
    include_package_data=True,
    install_requires=[
        'Click',
    ],
    entry_points={
        'console_scripts': [
            'efl = efl.optimize:cli'
        ]
    }
)