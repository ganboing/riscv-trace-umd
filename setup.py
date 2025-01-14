from setuptools import setup, find_packages, Extension

setup(
    name='rvtrace',
    version='0.1.20250114',
    description='User Mode driver for RISC-V Trace',
    url='https://github.com/ganboing/riscv-trace-umd',
    author='Bo Gan',
    author_email='ganboing@gmail.com',
    packages=find_packages(include='rvtrace.*'),
    package_data={'': ['*.cfg', '*.md']},
    entry_points={
        'console_scripts': ['rvtrace=rvtrace.cli:main']
    },
    ext_modules=[
        Extension(name='libmmio', sources=['lib/mmio.c'])
    ]
)
