"""setup.py."""
import os
from setuptools import setup, find_packages


def read(fname):
    """read."""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
        name='datadog-flask-blueprint',
        version='0.0.2',
        author='Gordon Simpson',
        author_email='gs@bn.co',
        description=('Flask blueprint for sending API statistics to datadog'),
        license='MIT',
        keywords='datadog,flask,blueprint,metrics',
        url='https://github.com/brandnetworks/datadog-flask-blueprint',
        packages=find_packages(),
        long_description=read('README.md'),
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Topic :: Utilities'
        ],
        install_requires=[
            'datadog',
            'flask'
        ]
)
