import os

def read_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def save_markdown(content: str, file_name: str = "result.md") -> str:
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, file_name)
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path