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
    ],
    author="Rejith R",
    author_email="rejithr1995@gmail.com",
    description="Razorpay Integration for ERPNext",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    license="MIT"
)