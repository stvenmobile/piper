import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'piper_drivers'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Include your driver launch targets
        (os.path.join('share', package_name, 'launch'), glob('launch/*_launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='steve',
    maintainer_email='stvenmobile@gmail.com',
    description='Piper Driver & Low-Level Perceptual Tier Nodes',
    license='TODO: License declaration',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'camera_node = piper_drivers.camera_node:main',
            'servo_node = piper_drivers.servo_node:main',
            'vision_tracking_node = piper_drivers.vision_tracking_node:main',
        ],
    },
)