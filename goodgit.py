import argparse
import sys
import os
from git import Repo, GitCommandError
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Conventional Commit Types
CONVENTIONAL_TYPES = [
    "feat", "fix", "docs", "style", "refactor",
    "perf", "test", "chore", "ci", "build"
]

class CommitGeneratorGUI:
    def __init__(self, master):
        self.master = master
        master.title("🎉 Auto Git Commit Message Generator")
        master.geometry("900x700")
        master.resizable(False, False)

        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6)
        style.configure("Header.TLabel", font=("Helvetica", 18, "bold"))
        style.configure("TCheckbutton", font=("Helvetica", 12))
        style.configure("TLabelFrame", font=("Helvetica", 12, "bold"))

        # Header
        self.header = ttk.Label(master, text="Auto Git Commit Message Generator", style="Header.TLabel")
        self.header.pack(pady=10)

        # Frame for file selection
        self.files_frame = ttk.LabelFrame(master, text="Changed Files")
        self.files_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Canvas and scrollbar for files
        self.canvas = tk.Canvas(self.files_frame)
        self.scrollbar = ttk.Scrollbar(self.files_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Dictionary to hold file checkboxes
        self.file_vars = {}

        # Populate files
        self.populate_files()

        # Frame for commit message
        self.commit_frame = ttk.LabelFrame(master, text="Commit Message")
        self.commit_frame.pack(fill="both", expand=False, padx=20, pady=10)

        self.text_area = scrolledtext.ScrolledText(self.commit_frame, wrap=tk.WORD, width=100, height=10, font=("Helvetica", 12))
        self.text_area.pack(padx=10, pady=10)

        # Frame for buttons
        self.buttons_frame = ttk.Frame(master)
        self.buttons_frame.pack(pady=10)

        self.generate_button = ttk.Button(self.buttons_frame, text="✨ Generate Commit Message", command=self.generate_message)
        self.generate_button.grid(row=0, column=0, padx=10, pady=5)

        self.commit_button = ttk.Button(self.buttons_frame, text="💾 Commit", command=self.commit_message)
        self.commit_button.grid(row=0, column=1, padx=10, pady=5)

        self.refresh_button = ttk.Button(self.buttons_frame, text="🔄 Refresh Files", command=self.refresh_files)
        self.refresh_button.grid(row=0, column=2, padx=10, pady=5)

        self.exit_button = ttk.Button(self.buttons_frame, text="❌ Exit", command=master.quit)
        self.exit_button.grid(row=0, column=3, padx=10, pady=5)

    def populate_files(self):
        """Populate the scrollable frame with changed files and checkboxes."""
        try:
            self.repo = get_repo()
            self.changed_files = self.repo.index.diff(None)

            # Clear previous checkboxes
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            self.file_vars.clear()

            if not self.changed_files:
                no_changes_label = ttk.Label(self.scrollable_frame, text="No changes detected.", foreground="red", font=("Helvetica", 12))
                no_changes_label.pack(pady=10)
                return

            for item in self.changed_files:
                file_path = item.a_path
                var = tk.BooleanVar(value=True)
                chk = ttk.Checkbutton(self.scrollable_frame, text=file_path, variable=var)
                chk.pack(anchor='w', padx=10, pady=2)
                self.file_vars[file_path] = var
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve changed files:\n{e}")

    def refresh_files(self):
        """Refresh the list of changed files."""
        self.populate_files()
        self.text_area.delete(1.0, tk.END)
        messagebox.showinfo("Refreshed", "File list has been refreshed.")

    def stage_selected_files(self):
        """Stage the selected files."""
        try:
            selected_files = [file for file, var in self.file_vars.items() if var.get()]
            if not selected_files:
                messagebox.showwarning("No Files Selected", "Please select at least one file to commit.")
                return False
            self.repo.index.add(selected_files)
            return True
        except GitCommandError as e:
            messagebox.showerror("Git Error", f"Failed to stage files:\n{e}")
            return False

    def generate_message(self):
        """Generate commit message using Groq AI based on selected changes."""
        if not self.stage_selected_files():
            return

        try:
            diff = self.repo.git.diff('--cached', '--pretty=format:')
            commit_message = self.call_groq_api(diff)
            if commit_message:
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, commit_message)
            else:
                messagebox.showerror("Error", "Failed to generate commit message.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{e}")

    def commit_message(self):
        """Commit the staged changes with the generated message."""
        commit_msg = self.text_area.get(1.0, tk.END).strip()
        if not commit_msg:
            messagebox.showwarning("No Commit Message", "Please generate a commit message before committing.")
            return
        try:
            self.repo.index.commit(commit_msg)
            messagebox.showinfo("Success", "Commit created successfully.")
            self.populate_files()
            self.text_area.delete(1.0, tk.END)
        except GitCommandError as e:
            messagebox.showerror("Git Error", f"Failed to create commit:\n{e}")

    def call_groq_api(self, diff_text):
        """Call the Groq API to generate a commit message."""
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            messagebox.showerror("API Key Missing", "GROQ_API_KEY environment variable not set.")
            return None

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
            messagebox.showerror("Groq API Error", f"An error occurred while calling the Groq API:\n{e}")
            return None

def get_repo():
    """Initialize and return the Git repository."""
    try:
        repo = Repo(os.getcwd(), search_parent_directories=True)
        if repo.bare:
            messagebox.showerror("Git Repository Error", "Repository is bare. Exiting.")
            sys.exit(1)
        return repo
    except Exception as e:
        messagebox.showerror("Git Repository Error", f"Error: {e}")
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

    try:
        repo = get_repo()
        changed_files = repo.index.diff(None)
        if not changed_files:
            print("No changed files detected.")
            sys.exit(0)

        # Stage all changes
        repo.git.add(all=True)

        # Get the diff
        diff = repo.git.diff('--cached', '--pretty=format:')

        # Call Groq API
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("Error: GROQ_API_KEY environment variable not set.")
            sys.exit(1)

        client = Groq(api_key=api_key)
        prompt = (
            "Generate a Conventional Commit message based on the following diff.\n"
            "Only provide the commit message without any additional text.\n\n"
            f"{diff}"
        )

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

        if args.commit:
            repo.index.commit(commit_message)
            print("Commit created successfully.")
        else:
            print("Generated Commit Message:")
            print(commit_message)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

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
