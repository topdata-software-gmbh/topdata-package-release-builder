from setuptools import setup, find_packages

setup(
    name="shopware-plugin-builder",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "rich>=13.0.0",
        "click>=8.0.0",
        "pytz",
    ],
    entry_points={
        'console_scripts': [
            'sw-build=shopware_plugin_builder.cli:main',
        ],
    },
)
