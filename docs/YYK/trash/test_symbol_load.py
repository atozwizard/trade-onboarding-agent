import os
import sys
import json

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.append(project_root)

print("--- sys.path ---")
for p in sys.path:
    print(p)

try:
    print("\n--- Importing backend.agents.riskmanaging.nodes ---")
    from backend.agents.riskmanaging import nodes
    print(f"Successfully imported nodes module from: {nodes.__file__}")

    print("\n--- dir(nodes) output ---")
    node_members = dir(nodes)
    for member in node_members:
        # Filter out built-in members and non-public ones for clarity
        if not member.startswith('__') and not member.startswith('_'):
            print(member)

    # Explicitly check for prepare_risk_state_node
    if 'prepare_risk_state_node' in node_members:
        print("\n'prepare_risk_state_node' found in dir(nodes).")
    else:
        print("\n'prepare_risk_state_node' NOT found in dir(nodes). This is unexpected.")

except ImportError as e:
    print(f"\nImportError during module import: {e}")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
