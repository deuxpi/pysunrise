#!/usr/bin/python

from distutils.core import setup

setup(name='pysunrise',
        version='0.1',
        author='Philippe Gauthier',
        author_email='philippe.gauthier@deuxpi.ca',
        url='http://www.deuxpi.ca/pysunrise/',
        description='Communicate with Solectria solar inverters',
        long_description='PySunrise is a Python library and scripts that can be used to communicate with Solectria PVI3000-7500 solar grid-tied inverters and build monitoring tools and real-time visualization applications.',
        download_url='https://gitorious.org/pysunrise/pysunrise',
        classifiers=[
            'Development Status :: 2 - Pre-Alpha',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'Intended Audience :: End Users/Desktop',
            'License :: OSI Approved :: GNU General Public License (GPL)',
            'Natural Language :: English',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Topic :: Home Automation',
            'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
            ],
        platforms='All',
        license='GPL3',
        scripts=['pysunrise'])

