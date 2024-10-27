from setuptools import setup, find_packages

with open('README.md', encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='nonebot-plugin-mai-arcade',
    version='0.1.5.7.4',
    description='maimai arcade nonebot2 plugin',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='YuuzukiRin',
    author_email='yuuzukirin@outlook.com',
    url='https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade',
    packages=find_packages(),
    install_requires=[
        'nonebot2>=2.2.0',
        'nonebot-plugin-localstore>=0.7.0',
        'nonebot-adapter-onebot>=2.4.4',
        'nonebot-plugin-apscheduler>=0.4.0',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',  
)


