import argparse
import sys
import os
from git import Repo
import tkinter as tk
from tkinter import messagebox, scrolledtext
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Conventional Commit Types
CONVENTIONAL_TYPES = [
    "feat", "fix", "docs", "style", "refactor",
    "perf", "test", "chore", "ci", "build"
]

def get_repo():
    """Initialize and return the Git repository."""
    try:
        repo = Repo(os.getcwd(), search_parent_directories=True)
        if repo.bare:
            print("Repository is bare. Exiting.")
            sys.exit(1)
        return repo
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def get_staged_changes(repo):
    """Retrieve staged changes in the repository."""
    staged_files = [item.a_path for item in repo.index.diff("HEAD")]
    return staged_files

def get_diff(repo):
    """Get the diff of staged changes."""
    diff = repo.git.diff('--cached', '--pretty=format:')
    return diff

def call_groq_api(diff_text):
    """Call the Groq API to generate a commit message."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable not set.")
        sys.exit(1)

    client = Groq(api_key=api_key)

    # Updated prompt to instruct AI to return only the commit message
    prompt = (
        "Generate a Conventional Commit message based on the following diff.\n"
        "Only provide the commit message without any additional text.\n\n"
        f"{diff_text}"
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-8b-8192",
        )
        commit_message = chat_completion.choices[0].message.content.strip()
        return commit_message
    except Exception as e:
        print(f"Groq API Error: {e}")
        return None

def generate_commit_message():
    """Generate commit message using Groq AI based on staged changes."""
    repo = get_repo()
    staged_files = get_staged_changes(repo)
    if not staged_files:
        print("No staged changes found.")
        sys.exit(0)

    # Get the diff of staged changes
    diff = get_diff(repo)

    commit_message = call_groq_api(diff)

    if commit_message:
        # Print only the commit message without additional text
        print(commit_message)
        return commit_message
    else:
        print("Failed to generate commit message.")
        sys.exit(1)

def cli():
    """Command-Line Interface."""
    parser = argparse.ArgumentParser(
        description="Auto-generate Git commit messages following Conventional Commits."
    )
    parser.add_argument(
        '--commit',
        action='store_true',
        help='Generate and commit with the auto-generated message.'
    )
    args = parser.parse_args()

    commit_message = generate_commit_message()
    if args.commit:
        repo = get_repo()
        try:
            repo.index.commit(commit_message)
            print("Commit created successfully.")
        except Exception as e:
            print(f"Failed to create commit: {e}")
    else:
        print("Use --commit to create a commit with the generated message.")

class CommitGeneratorGUI:
    def __init__(self, master):
        self.master = master
        master.title("Auto Git Commit Message Generator")

        self.label = tk.Label(master, text="Auto Git Commit Message Generator", font=("Helvetica", 16))
        self.label.pack(pady=10)

        self.text_area = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=80, height=20)
        self.text_area.pack(padx=10, pady=10)

        self.generate_button = tk.Button(master, text="Generate Commit Message", command=self.generate_message)
        self.generate_button.pack(pady=5)

        self.commit_button = tk.Button(master, text="Commit", command=self.commit_message)
        self.commit_button.pack(pady=5)

    def generate_message(self):
        try:
            commit_message = generate_commit_message()
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, commit_message)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def commit_message(self):
        commit_message = self.text_area.get(1.0, tk.END).strip()
        if not commit_message:
            messagebox.showwarning("Warning", "No commit message to commit.")
            return
        try:
            repo = get_repo()
            repo.index.commit(commit_message)
            messagebox.showinfo("Success", "Commit created successfully.")
            self.text_area.delete(1.0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", str(e))

def gui():
    """Graphical User Interface."""
    root = tk.Tk()
    gui_app = CommitGeneratorGUI(root)
    root.mainloop()

def main():
    parser = argparse.ArgumentParser(
        description="Auto-generate Git commit messages following Conventional Commits."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--gui', action='store_true', help='Launch GUI mode.')
    group.add_argument('--cli', action='store_true', help='Launch CLI mode.')
    args = parser.parse_args()

    if args.gui:
        gui()
    else:
        cli()

if __name__ == "__main__":
    main()

# Example of Desired Output:
# feat: Add LICENSE.txt file and CLI/GUI functionality for auto-generating Conventional Commit messages
