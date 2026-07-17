import os
from PIL import Image, ImageDraw, ImageFont

# Define paths
FONT_REGULAR_PATH = "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
FONT_MONO_PATH = "/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf"
OUTPUT_PATH = "/home/iinx-user/trackify-ai-parth/architecture/self_correction_loop.png"

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# Image dimensions
W, H = 1100, 650
bg_color = (18, 18, 24) # #121218 (Very dark purple/black)
img = Image.new("RGBA", (W, H), bg_color)
draw = ImageDraw.Draw(img)

# Try loading fonts, fallback if not found
try:
    font_title = ImageFont.truetype(FONT_BOLD_PATH, 26)
    font_section = ImageFont.truetype(FONT_BOLD_PATH, 16)
    font_body = ImageFont.truetype(FONT_REGULAR_PATH, 13)
    font_mono = ImageFont.truetype(FONT_MONO_PATH, 12)
    font_label = ImageFont.truetype(FONT_REGULAR_PATH, 12)
except Exception:
    # Fallback to default
    font_title = font_section = font_body = font_mono = font_label = ImageFont.load_default()

# Colors
color_blue = (59, 130, 246, 255)       # #3b82f6 (Input)
color_purple = (139, 92, 246, 255)     # #8b5cf6 (LLM Gen)
color_amber = (245, 158, 11, 255)      # #f59e0b (DB Execution)
color_emerald = (16, 185, 129, 255)    # #10b981 (Success Check)
color_red = (239, 68, 68, 255)         # #ef4444 (Failure)
color_magenta = (217, 70, 239, 255)    # #d946ef (Correction)
color_green_dark = (5, 150, 105, 255)  # #059669 (Output Node)
color_text_white = (255, 255, 255, 255)
color_text_gray = (156, 163, 175, 255)
color_line_gray = (75, 85, 99, 255)
color_line_red = (239, 68, 68, 180)

# Draw Title Header
draw.rectangle([(0, 0), (W, 70)], fill=(30, 30, 39, 255))
draw.text((30, 20), "Trackify AI: Self-Correcting LangGraph Query Loop", fill=color_text_white, font=font_title)
draw.line([(0, 70), (W, 70)], fill=(75, 85, 99, 255), width=2)

# Helper function to draw rounded boxes with text
def draw_node(x, y, w, h, bg_color, title, lines=None, line_spacing=18, is_diamond=False):
    # Draw shadow
    draw.rounded_rectangle([(x+4, y+4), (x+w+4, y+h+4)], radius=8, fill=(0, 0, 0, 80))
    # Draw box
    draw.rounded_rectangle([(x, y), (x+w, y+h)], radius=8, fill=bg_color, outline=(255,255,255,40), width=1)
    
    # Title text
    tx = x + w//2
    ty = y + 15
    draw.text((tx, ty), title, fill=color_text_white, font=font_section, anchor="mm")
    
    # Divider line if there is body text
    if lines:
        draw.line([(x + 15, y + 30), (x + w - 15, y + 30)], fill=(255, 255, 255, 40), width=1)
        # Body text
        curr_y = y + 42
        for line in lines:
            draw.text((tx, curr_y), line, fill=(240, 240, 250, 255), font=font_body, anchor="mm")
            curr_y += line_spacing

def draw_diamond_node(x, y, r, bg_color, title, label=""):
    # Center is at (x, y), half-width/height is r
    coords = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
    # Draw shadow
    shadow_coords = [(cx+3, cy+3) for cx, cy in coords]
    draw.polygon(shadow_coords, fill=(0, 0, 0, 80))
    # Draw main polygon
    draw.polygon(coords, fill=bg_color, outline=(255, 255, 255, 60), width=1)
    # Title
    draw.text((x, y), title, fill=color_text_white, font=font_section, anchor="mm")
    if label:
        draw.text((x, y - r - 15), label, fill=color_text_gray, font=font_body, anchor="mm")

# Coordinates of nodes
# 1. User input
node_input = {"x": 40, "y": 120, "w": 230, "h": 100}
# 2. execute_query_gen (Node 2c)
node_gen = {"x": 350, "y": 120, "w": 280, "h": 130}
# 3. DB aggregate (Middle stage)
node_db = {"x": 750, "y": 120, "w": 280, "h": 130}
# 4. Decision Diamond
node_decision = {"x": 890, "y": 380, "r": 70}
# 5. format_answer (Node 3)
node_success = {"x": 750, "y": 510, "w": 280, "h": 100}
# 6. correct_query_gen (Node 2d)
node_correct = {"x": 350, "y": 315, "w": 280, "h": 130}

# Draw Nodes
draw_node(node_input["x"], node_input["y"], node_input["w"], node_input["h"], color_blue, 
          "1. User Question & State", 
          ["Inputs: User text, chat history", "Schema Context: timeentries,", "users, projects, groups"])

draw_node(node_gen["x"], node_gen["y"], node_gen["w"], node_gen["h"], color_purple, 
          "2. execute_query_gen Node", 
          ["Model: Gemini 2.5 Flash", "Task: Generate MongoDB pipeline", "Output: JSON query string", "(e.g., unwind, match, group)"])

draw_node(node_db["x"], node_db["y"], node_db["w"], node_db["h"], color_amber, 
          "3. DB Execution & Validation", 
          ["Step 1: Check validation filters", "Step 2: Run PyMongo aggregate()", "Output: Query results OR", "MongoDB exception thrown"])

draw_diamond_node(node_decision["x"], node_decision["y"], node_decision["r"], color_emerald, "Success?")

draw_node(node_success["x"], node_success["y"], node_success["w"], node_success["h"], color_green_dark, 
          "4. format_answer Node", 
          ["Model: Llama 3.1 8B (Formatter)", "Result: Natural English", "sentence mapping the metrics"])

draw_node(node_correct["x"], node_correct["y"], node_correct["w"], node_correct["h"], color_magenta, 
          "Self-Correction Node", 
          ["Model: Llama 3.1 70B", "Input: FAILED pipeline + ERROR text", "Goal: Analyze syntax bug & fix JSON", "Output: New corrected pipeline"])

# Draw Connective Lines & Arrows
def draw_arrow(start, end, color=color_line_gray, width=2, is_dashed=False):
    # start: (x1, y1), end: (x2, y2)
    x1, y1 = start
    x2, y2 = end
    
    # Draw line
    draw.line([start, end], fill=color, width=width)
    
    # Draw arrowhead pointing towards 'end'
    # Determine direction
    dx = x2 - x1
    dy = y2 - y1
    length = (dx**2 + dy**2)**0.5
    if length > 0:
        ux = dx / length
        uy = dy / length
        # Arrowhead coordinates
        arrow_size = 8
        p1 = (x2 - ux * arrow_size + uy * (arrow_size / 1.5), y2 - uy * arrow_size - ux * (arrow_size / 1.5))
        p2 = (x2 - ux * arrow_size - uy * (arrow_size / 1.5), y2 - uy * arrow_size + ux * (arrow_size / 1.5))
        draw.polygon([end, p1, p2], fill=color)

# 1. Input -> Gen
draw_arrow((node_input["x"] + node_input["w"], node_input["y"] + node_input["h"]//2), 
           (node_gen["x"], node_gen["y"] + node_gen["h"]//2))

# 2. Gen -> DB
draw_arrow((node_gen["x"] + node_gen["w"], node_gen["y"] + node_gen["h"]//2), 
           (node_db["x"], node_db["y"] + node_db["h"]//2))

# 3. DB -> Decision
draw_arrow((node_db["x"] + node_db["w"]//2, node_db["y"] + node_db["h"]), 
           (node_decision["x"], node_decision["y"] - node_decision["r"]))

# 4. Decision -> Success (YES branch)
draw_arrow((node_decision["x"], node_decision["y"] + node_decision["r"]), 
           (node_success["x"] + node_success["w"]//2, node_success["y"]),
           color=color_emerald, width=3)
draw.text((node_decision["x"] + 15, node_decision["y"] + node_decision["r"] + 25), "YES", fill=color_emerald, font=font_section)

# 5. Decision -> Self-Correction Node (NO branch)
# This loops leftward. We'll draw a right-angle line
corner_pt = (node_correct["x"] + node_correct["w"]//2, node_decision["y"])
draw.line([(node_decision["x"] - node_decision["r"], node_decision["y"]), corner_pt], fill=color_red, width=3)
draw_arrow(corner_pt, (node_correct["x"] + node_correct["w"]//2, node_correct["y"] + node_correct["h"]), color=color_red, width=3)
draw.text((node_decision["x"] - node_decision["r"] - 40, node_decision["y"] - 15), "NO", fill=color_red, font=font_section)
draw.text((corner_pt[0] + 10, corner_pt[1] + 20), "Feeds error back\nto LLM (retry_count < 1)", fill=color_red, font=font_body)

# 6. Self-Correction Node -> DB Node (Re-execution path)
# From top of correct node, we go up, right, and into the left of DB execution
start_pt = (node_correct["x"] + node_correct["w"]//2, node_correct["y"])
corner_pt2 = (node_correct["x"] + node_correct["w"]//2, 85)
corner_pt3 = (700, 85)
draw.line([start_pt, corner_pt2], fill=color_magenta, width=3)
draw.line([corner_pt2, corner_pt3], fill=color_magenta, width=3)
draw_arrow(corner_pt3, (node_db["x"], node_db["y"] + 25), color=color_magenta, width=3)
draw.text((node_correct["x"] + node_correct["w"]//2 + 10, 95), "Re-executes corrected query", fill=color_magenta, font=font_body)

# Add decorative legend / description boxes
draw.rectangle([(40, 270), (270, 610)], fill=(24, 24, 37, 255), outline=(75, 85, 99, 255))
draw.text((55, 285), "Why Self-Correction?", fill=color_magenta, font=font_section)
desc_lines = [
    "LLMs can generate invalid JSON,",
    "refer to non-existent collections,",
    "or use Mongo shell-only helpers",
    "like ISODate() or ObjectId()",
    "which crash python's BSON parser.",
    "",
    "Instead of showing a raw error,",
    "the Graph catches the Exception,",
    "increments retry_count, and",
    "routes to correct_query_gen.",
    "",
    "The correction prompt sends the",
    "exact failed JSON query along",
    "with the specific traceback",
    "error back to the LLM to write",
    "a corrected pipeline.",
    "This prevents 99% of crashes."
]
curr_y = 315
for line in desc_lines:
    draw.text((55, curr_y), line, fill=color_text_gray, font=font_body)
    curr_y += 16

# Save image
img.save(OUTPUT_PATH)
print(f"Successfully generated custom self-correction diagram at {OUTPUT_PATH}")
