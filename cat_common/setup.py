import pathlib
from datetime import datetime

# Always prefer setuptools over distutils
from setuptools import find_packages, setup

here = pathlib.Path(__file__).parent.resolve()


setup(
    name="cat_common",  # Required
    version=datetime.now().strftime("%Y.%m.%d%H%M"),
    description="Ghostly Cat common libraries",
    packages=find_packages(),
    python_requires=">=3.6, <4",
    install_requires=[
        "paho-mqtt==1.6.1",
    ],
)
