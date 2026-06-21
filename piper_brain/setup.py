from setuptools import find_packages, setup

package_name = 'piper_brain'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='steve',
    maintainer_email='stvenmobile@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'camera_node = piper_brain.camera_node:main',
            'servo_node = piper_brain.servo_node:main',
            'vision_tracking_node = piper_brain.vision_tracking_node:main',
            'dashboard = piper_brain.dashboard:main',  # <-- MAKE SURE THIS LINE EXISTS
        ],
    },
)
