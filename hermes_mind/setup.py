from setuptools import find_packages, setup

package_name = 'hermes_mind'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'requests'],
    zip_safe=True,
    maintainer='Steve',
    maintainer_email='steve@todo.todo',
    description='Hermes Agent background task supervisor and code optimization engine',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'task_supervisor = hermes_mind.task_supervisor:main',
        ],
    },
)