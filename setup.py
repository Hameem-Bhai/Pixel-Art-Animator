from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pixel-animator",
    version="1.0.0",
    author="Hameem",
    author_email="your-email@example.com",
    description="A Python tool for creating and playing pixel art animations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pixel-animator",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Artistic Software",
    ],
    python_requires=">=3.7",
    install_requires=[
        "Pillow>=9.0.0",
        "imageio>=2.9.0",
    ],
    entry_points={
        "console_scripts": [
            "pixel-animator=pixel_animator:main",
        ],
    },
)