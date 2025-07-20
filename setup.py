from setuptools import setup, find_packages

setup(
    name="razorpay_integration",
    version="0.0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "frappe",
        "razorpay",
        "requests"
    ]
)