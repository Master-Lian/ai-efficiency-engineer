import os
from utils.file_io import read_text, save_markdown
from utils.ai_summarizer import summarize_text

if __name__ == "__main__":
    input_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input")

    for file_name in os.listdir(input_path):
        if file_name.endswith(".txt"):
            print(f"Processing {file_name}...")
            file_path = os.path.join(input_path, file_name)
            text = read_text(file_path)
            summary = summarize_text(text)
            print(summary)
            output_file_name = f"{os.path.splitext(file_name)[0]}_summary.md"
            output_path = save_markdown(summary, output_file_name)
    
    print("\n All files processed. Summaries saved in the output directory.")