from setuptools import setup, find_packages

setup(
    name="games_elt",
    version="0.1.0",
    package_dir={"": "."},
    packages=find_packages(where="."),
    install_requires=[
        "requests>=2.25.0",
        "python-dotenv>=0.19.0",
        "pydantic>=2.0.0",
        "pandas>=1.3.0"
    ],
    extras_require={
        "test": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "pytest-asyncio>=0.21.1",
            "requests-mock>=1.11.0",
            "coverage>=7.3.2"
        ]
    },
    python_requires=">=3.8",
    author="Burakhan",
    description="A package for collecting and processing game data",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ]
) 