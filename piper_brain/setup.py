from setuptools import find_packages, setup
import os

package_name = 'piper_brain'

# --- CLEAN ASSET EXTRACTION TREE ---
def get_flat_data_files(source_dir, target_share_path):
    """
    Walks the source directory and strips prefixes so files copy 
    directly into the root of the target share path destination.
    """
    data_files_map = []
    for root, dirs, filenames in os.walk(source_dir):
        for filename in filenames:
            source_file_path = os.path.join(root, filename)
            
            # Calculate where this file should drop relative to the share destination
            relative_path = os.path.relpath(root, source_dir)
            if relative_path == ".":
                destination_dir = target_share_path
            else:
                destination_dir = os.path.join(target_share_path, relative_path)
                
            data_files_map.append((destination_dir, [source_file_path]))
    return data_files_map

# Build direct target destination mappings
data_files_list = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
]

# Dynamically append flattened front-end files
data_files_list.extend(get_flat_data_files('piper_brain/templates', 'share/' + package_name + '/templates'))
data_files_list.extend(get_flat_data_files('piper_brain/assets', 'share/' + package_name + '/assets'))

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=data_files_list,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='steve',
    maintainer_email='steve@todo.todo',
    description='Decoupled Object Telemetry Dashboard Core for Piper Assistant Stack',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'dashboard_node = piper_brain.dashboard_node:main'
        ],
    },
)