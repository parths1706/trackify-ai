import os
import sys

# Add backend directory to sys.path so we can import services
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.graph_service import compiled_graph

try:
    png_bytes = compiled_graph.get_graph().draw_mermaid_png()
    output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'architecture', 'langgraph_flow.png')
    
    # Ensure architecture directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'wb') as f:
        f.write(png_bytes)
    print(f"Successfully generated graph image at {output_path}")
except Exception as e:
    print(f"Error generating graph image: {e}")
