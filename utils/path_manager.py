import os
import yaml
import datetime

class PathManager:
    def __init__(self, config_path=None):
        if config_path is None:
            # Default to config/paths.yaml relative to this file
            # Current file is in utils/, so we need to go up one level
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, 'config', 'paths.yaml')
            
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
    def get_path(self, key, basename, **kwargs):
        """
        Get a resolved absolute path for a given key.
        
        Args:
            key: Key in the 'files' section of config (e.g., 'srt', 'final_mix')
                 or a direct key like 'project_root' or 'intermediate_dir'.
            basename: The base name of the project/file.
            **kwargs: Additional variables to format (e.g., timestamp).
            
        Returns:
            str: Resolved absolute path.
        """
        # Prepare context variables
        timestamp = kwargs.get('timestamp', datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        # 1. Resolve Project Root
        root_template = self.config.get('project_root', 'data/{basename}')
        project_root = root_template.format(basename=basename)
        project_root = os.path.abspath(project_root)
        
        # 2. Resolve Intermediate Dir
        inter_template = self.config.get('intermediate_dir', '{project_root}/intermediate')
        intermediate_dir = inter_template.format(project_root=project_root)
        
        context = {
            'basename': basename,
            'project_root': project_root,
            'intermediate_dir': intermediate_dir,
            'timestamp': timestamp,
            **kwargs
        }
        
        # Determine the template
        if key in self.config:
            template = self.config[key]
        elif key in self.config.get('files', {}):
            template = self.config['files'][key]
        else:
            raise KeyError(f"Path key '{key}' not found in configuration.")
            
        # Format the path
        path = template.format(**context)
        
        # Ensure directory exists
        dir_path = os.path.dirname(path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            
        return path

    def get_project_dir(self, basename):
        return self.get_path('project_root', basename)
        
    def get_intermediate_dir(self, basename):
        return self.get_path('intermediate_dir', basename)
