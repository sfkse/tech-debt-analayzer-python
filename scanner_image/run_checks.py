import json
import sys
import os
import importlib
import inspect
from plugins.base_plugin import BasePlugin

def discover_plugins() -> list[BasePlugin]:
    """Dynamically discovers and instantiates all plugins in the 'plugins' directory."""
    plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
    plugins = []
    # Add plugin dir to path to allow imports
    sys.path.append(os.path.dirname(__file__))

    for f in os.listdir(plugin_dir):
        if f.endswith(".py") and f != "base_plugin.py" and not f.startswith("__"):
            module_name = f"plugins.{f[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                        plugins.append(obj()) # Instantiate the plugin
                        print(f"Discovered plugin: {name}")
            except Exception as e:
                print(f"Could not import or instantiate plugin from {f}: {e}", file=sys.stderr)
    return plugins

def main():
    """Main function to run checks and write results."""
    repo_path = "/repo"
    output_path = "/output/results.json"
    
    print("Discovering plugins...")
    plugins_to_run = discover_plugins()
    
    if not plugins_to_run:
        print("No plugins found. Exiting.", file=sys.stderr)
        sys.exit(0) # Exit gracefully if no plugins

    all_issues = []
    print(f"\nRunning checks on repository: {repo_path}")
    
    for plugin in plugins_to_run:
        plugin_name = plugin.__class__.__name__
        try:
            print(f"--- Running plugin: {plugin_name} ---")
            issues = plugin.run(repo_path)
            if issues:
                all_issues.extend(issues)
            print(f"--- Finished plugin: {plugin_name} ---")
        except Exception as e:
            print(f"Error running plugin {plugin_name}: {e}", file=sys.stderr)
    
    print(f"\nFound a total of {len(all_issues)} issues across all plugins.")
    
    try:
        with open(output_path, "w") as f:
            json.dump(all_issues, f, indent=2)
        print(f"Results written to {output_path}")
    except IOError as e:
        print(f"Error writing results to {output_path}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
