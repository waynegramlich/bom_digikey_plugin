import os
import setuptools

def long_description_read():
    with open("README.md") as readme_file:
        long_description = readme_file.read()
    return long_description

environment = os.environ
assert "BOM_VERSION" in environment, "BOM_VERSION environment variable is not set"
version = environment["BOM_VERSION"]

# Arguments to *setup*() are in alphabetical order:
setuptools.setup(
    author="Wayne Gramlich",
    author_email="Wayne@Gramlich.Net",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    description="Bill Of Materials Manager",
    entry_points = {
        "console_scripts": ["bom_digikey=bom_digikey_plugin:main"],
        "bom_manager_collection_url_load": ["url_load=bom_digikey_plugin.digikey:url_load"],
    },
    include_package_data=True,
    # install_requires = [
    #     "bs4",
    # ],
    license="MIT",
    long_description=long_description_read(),
    long_description_content_type="text/markdown",
    name="bom_digikey_plugin_waynegramlich",
    packages=[
        "bom_digikey_plugin",
    ],
    python_requires=">=3.6",
    url="https://github.com/waynegramlich/bom_digikey_plugin",
    version=version,
)
