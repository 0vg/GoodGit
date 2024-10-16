import argparse
import sys
import os
from git import Repo, GitCommandError
import customtkinter as ctk
from tkinter import messagebox, scrolledtext, filedialog
import tkinter as tk
from groq import Groq
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    filename='goodgit.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables from .env file
load_dotenv()

# Conventional Commit Types
CONVENTIONAL_TYPES = [
    "feat", "fix", "docs", "style", "refactor",
    "perf", "test", "chore", "ci", "build"
]

class CommitGeneratorGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.repo = None
        self.file_vars = {}

        # Configure window
        self.title("🎉 Auto Git Commit Message Generator")
        self.geometry("1000x700")
        self.resizable(False, False)

        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        # Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Git Commit\nGenerator",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Change Directory Button
        self.change_dir_button = ctk.CTkButton(
            self.sidebar_frame,
            text="📂 Change Directory",
            command=self.change_directory
        )
        self.change_dir_button.grid(row=1, column=0, padx=20, pady=10)

        # Appearance Mode
        self.appearance_mode_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Appearance Mode:",
            anchor="w"
        )
        self.appearance_mode_label.grid(row=2, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event
        )
        self.appearance_mode_optionemenu.grid(row=3, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu.set("System")

        # UI Scaling
        self.scaling_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="UI Scaling:",
            anchor="w"
        )
        self.scaling_label.grid(row=4, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling_event
        )
        self.scaling_optionemenu.grid(row=5, column=0, padx=20, pady=(10, 20))
        self.scaling_optionemenu.set("100%")

        # Main frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Repository Path Display
        self.repo_path_label = ctk.CTkLabel(
            self.main_frame,
            text="Repository Path:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.repo_path_label.grid(row=0, column=0, sticky="w")

        self.repo_path_display = ctk.CTkLabel(
            self.main_frame,
            text="Not Selected",
            font=ctk.CTkFont(size=12)
        )
        self.repo_path_display.grid(row=0, column=1, sticky="w", padx=(10, 0))

        # Changed Files Label
        self.files_label = ctk.CTkLabel(
            self.main_frame,
            text="Changed Files:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.files_label.grid(row=1, column=0, sticky="w", pady=(20, 0))

        # Scrollable Frame for Changed Files
        self.scrollable_frame = ctk.CTkScrollableFrame(self.main_frame, corner_radius=10)
        self.scrollable_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 10))

        # Commit Message Label
        self.commit_label = ctk.CTkLabel(
            self.main_frame,
            text="Commit Message:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.commit_label.grid(row=3, column=0, sticky="w", pady=(20, 0))

        # Commit Message Text Area
        self.text_area = scrolledtext.ScrolledText(
            self.main_frame,
            wrap='word',
            width=80,
            height=10,
            font=("Helvetica", 12),
            bg=self._get_text_area_bg(),
            fg=self._get_text_area_fg(),
            insertbackground=self._get_text_area_fg()
        )
        self.text_area.grid(row=4, column=0, columnspan=2, padx=(0, 20), pady=(10, 20), sticky="nsew")

        # Buttons Frame
        self.buttons_frame = ctk.CTkFrame(self.main_frame)
        self.buttons_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")
        self.buttons_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Define a smaller font for buttons
        button_font = ctk.CTkFont(size=12, weight="bold")

        # Generate Commit Message Button
        self.generate_button = ctk.CTkButton(
            self.buttons_frame,
            text="✨ Generate Commit Message",
            command=self.generate_message,
            state="disabled",
            font=button_font
        )
        self.generate_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Commit Button
        self.commit_button = ctk.CTkButton(
            self.buttons_frame,
            text="💾 Commit",
            command=self.commit_message,
            state="disabled",
            font=button_font
        )
        self.commit_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Push Button
        self.push_button = ctk.CTkButton(
            self.buttons_frame,
            text="🚀 Push",
            command=self.push_commit,
            state="disabled",
            font=button_font
        )
        self.push_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # Refresh Files Button
        self.refresh_button = ctk.CTkButton(
            self.buttons_frame,
            text="🔄 Refresh Files",
            command=self.refresh_files,
            state="disabled",
            font=button_font
        )
        self.refresh_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # Exit Button
        self.exit_button = ctk.CTkButton(
            self.buttons_frame,
            text="❌ Exit",
            command=self.quit,
            font=button_font
        )
        self.exit_button.grid(row=0, column=4, padx=5, pady=5, sticky="ew")

        # Attempt to set the default repository path to current directory
        self.repo_path = os.getcwd()
        if not self.set_repository(self.repo_path):
            # If setting repository failed, prompt user to select one
            self.prompt_repository_selection()

        # Apply initial theme to ScrolledText and ScrollableFrame
        self.update_scrolledtext_colors()
        self.update_scrollable_frame_colors()

    def _get_text_area_bg(self):
        """Get the background color for the ScrolledText based on the current theme."""
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            return "#2B2B2B"
        else:
            return "#FFFFFF"

    def _get_text_area_fg(self):
        """Get the foreground color for the ScrolledText based on the current theme."""
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            return "#FFFFFF"
        else:
            return "#000000"

    def _get_scrollable_frame_bg(self):
        """Get the background color for the ScrollableFrame based on the current theme."""
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            return "#2B2B2B"
        else:
            return "#FFFFFF"

    def change_appearance_mode_event(self, new_appearance_mode: str):
        """Change the appearance mode of the application."""
        ctk.set_appearance_mode(new_appearance_mode)
        self.update_scrolledtext_colors()
        self.update_scrollable_frame_colors()

    def change_scaling_event(self, new_scaling: str):
        """Change the scaling of the application."""
        try:
            new_scaling_float = int(new_scaling.replace("%", "")) / 100
            ctk.set_widget_scaling(new_scaling_float)
        except ValueError:
            messagebox.showerror("Invalid Scaling", "Please select a valid scaling percentage.")

    def update_scrolledtext_colors(self):
        """Update the ScrolledText widget colors based on the current appearance mode."""
        self.text_area.configure(
            bg=self._get_text_area_bg(),
            fg=self._get_text_area_fg(),
            insertbackground=self._get_text_area_fg()
        )

    def update_scrollable_frame_colors(self):
        """Update the ScrollableFrame colors based on the current theme."""
        bg_color = self._get_scrollable_frame_bg()
        self.scrollable_frame.configure(fg_color=bg_color)

    def change_directory(self):
        """Open a dialog to select a new repository directory."""
        selected_dir = filedialog.askdirectory()
        if selected_dir:
            if not os.path.isdir(os.path.join(selected_dir, '.git')):
                messagebox.showerror("Invalid Repository", "The selected directory is not a Git repository.")
                return
            if self.set_repository(selected_dir):
                messagebox.showinfo("Repository Set", f"Repository set to:\n{selected_dir}")
            else:
                self.prompt_repository_selection()

    def set_repository(self, path):
        """Set the current repository path and update the GUI."""
        try:
            repo = Repo(path)
            if repo.bare:
                messagebox.showerror("Git Repository Error", "Selected repository is bare. Please choose a valid Git repository.")
                return False
            self.repo = repo
            self.repo_path = path
            self.repo_path_display.configure(text=self.repo_path)
            self.populate_files()
            self.enable_buttons()
            return True
        except Exception as e:
            messagebox.showerror("Git Repository Error", f"Failed to set repository:\n{e}")
            self.repo = None  # Ensure repo is set to None on failure
            self.disable_buttons()
            return False

    def prompt_repository_selection(self):
        """Prompt the user to select a Git repository."""
        messagebox.showinfo("Select Repository", "Please select a Git repository to proceed.")
        self.change_directory()

    def enable_buttons(self):
        """Enable commit, push, and refresh buttons."""
        self.generate_button.configure(state="normal")
        self.commit_button.configure(state="normal")
        self.push_button.configure(state="normal")
        self.refresh_button.configure(state="normal")

    def disable_buttons(self):
        """Disable commit, push, and refresh buttons."""
        self.generate_button.configure(state="disabled")
        self.commit_button.configure(state="disabled")
        self.push_button.configure(state="disabled")
        self.refresh_button.configure(state="disabled")

    def populate_files(self, max_files=50):
        """Populate the scrollable frame with changed files and checkboxes."""
        try:
            if not self.repo:
                # Repository is not set; prompt user to select a valid repository
                messagebox.showerror("Repository Error", "No valid Git repository selected.")
                return

            # Retrieve changes
            unstaged_changes = self.repo.index.diff(None)
            staged_changes = self.repo.index.diff("HEAD")
            untracked_files = self.repo.untracked_files

            # Combine all changes into a single list with change types
            changed_files = []

            # Add staged changes
            for item in staged_changes:
                changed_files.append((item.a_path, 'staged'))

            # Add unstaged changes
            for item in unstaged_changes:
                changed_files.append((item.a_path, 'unstaged'))

            # Add untracked files
            for file_path in untracked_files:
                changed_files.append((file_path, 'untracked'))

            # Limit the number of displayed files
            if len(changed_files) > max_files:
                messagebox.showwarning(
                    "File Limit Reached",
                    f"Only the first {max_files} changed files are displayed. Please commit remaining changes separately."
                )
                changed_files = changed_files[:max_files]

            # Clear previous checkboxes
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            self.file_vars.clear()

            if not changed_files:
                no_changes_label = ctk.CTkLabel(
                    self.scrollable_frame,
                    text="No changes detected.",
                    fg_color=("red", "#FFCCCC"),
                    text_color="black"
                )
                no_changes_label.pack(pady=10, padx=10, fill="x")
                return

            for file_path, status in changed_files:
                var = tk.BooleanVar(value=True)
                chk = ctk.CTkCheckBox(
                    self.scrollable_frame,
                    text=f"{file_path} [{status}]",
                    variable=var
                )
                chk.pack(anchor='w', padx=10, pady=2)
                self.file_vars[file_path] = var

        except AttributeError as e:
            messagebox.showerror("Error", f"Failed to retrieve changed files:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve changed files:\n{e}")

    def refresh_files(self):
        """Refresh the list of changed files."""
        self.populate_files()
        self.text_area.delete(1.0, tk.END)  # Changed to tk.END
        messagebox.showinfo("Refreshed", "File list has been refreshed.")

    def stage_selected_files(self):
        """Stage the selected files."""
        try:
            if not self.repo:
                messagebox.showerror("Repository Error", "No valid Git repository selected.")
                return False

            selected_files = [file for file, var in self.file_vars.items() if var.get()]
            if not selected_files:
                messagebox.showwarning("No Files Selected", "Please select at least one file to commit.")
                return False
            self.repo.index.add(selected_files)
            return True
        except GitCommandError as e:
            messagebox.showerror("Git Error", f"Failed to stage files:\n{e}")
            return False

    def generate_message(self, max_retries=3):
        """Generate commit message using Groq AI based on selected changes."""
        if not self.stage_selected_files():
            return

        try:
            diff = self.repo.git.diff('--cached', '--pretty=format:')
            limited_diff, was_truncated = self.limit_diff_size(diff, max_size=5000)

            if was_truncated:
                messagebox.showwarning(
                    "Diff Truncated",
                    "The diff is too large and has been truncated to fit the API limits."
                )

            for attempt in range(1, max_retries + 1):
                commit_message = self.call_groq_api(limited_diff)
                if commit_message:
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(tk.END, commit_message)
                    return  # Successful generation; exit the method
                else:
                    logging.warning(f"Attempt {attempt}: Failed to generate a valid commit message.")
                    if attempt < max_retries:
                        logging.info("Retrying to generate commit message...")
            # After max_retries attempts, allow manual input
            response = messagebox.askyesno(
                "Generate Commit Message",
                "Failed to generate a valid commit message after multiple attempts.\nWould you like to enter it manually?"
            )
            if response:
                self.text_area.delete(1.0, tk.END)
                # The user can now type their commit message in the text area
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{e}")

    def limit_diff_size(self, diff_text, max_size=5000):
        """
        Limits the size of the diff_text to max_size characters.

        Parameters:
            diff_text (str): The full diff text.
            max_size (int): The maximum allowed size in characters.

        Returns:
            tuple: (limited_diff_text, was_truncated)
        """
        if len(diff_text) > max_size:
            # Split the diff into individual file diffs
            file_diffs = diff_text.split('\ndiff --git')
            limited_diff = ""
            for file_diff in file_diffs:
                # Reconstruct the diff for each file
                reconstructed_diff = f"\ndiff --git{file_diff}"
                if len(limited_diff) + len(reconstructed_diff) > max_size:
                    break
                limited_diff += reconstructed_diff
            was_truncated = len(limited_diff) < len(diff_text)
            return limited_diff, was_truncated
        return diff_text, False

    def commit_message(self):
        """Commit the staged changes with the generated message."""
        if not self.repo:
            messagebox.showerror("Repository Error", "No valid Git repository selected.")
            return

        commit_msg = self.text_area.get(1.0, tk.END).strip()
        if not commit_msg:
            messagebox.showwarning("No Commit Message", "Please generate a commit message before committing.")
            return
        try:
            self.repo.index.commit(commit_msg)
            messagebox.showinfo("Success", "Commit created successfully.")
            self.populate_files()
            self.text_area.delete(1.0, tk.END)  # Changed to tk.END
        except GitCommandError as e:
            messagebox.showerror("Git Error", f"Failed to create commit:\n{e}")

    def push_commit(self):
        """Push the latest commit to the remote repository."""
        if not self.repo:
            messagebox.showerror("Repository Error", "No valid Git repository selected.")
            return

        try:
            origin = self.repo.remote(name='origin')
            origin.push()
            messagebox.showinfo("Success", "Pushed to remote repository successfully.")
        except GitCommandError as e:
            messagebox.showerror("Push Error", f"Failed to push to remote repository:\n{e}")
        except AttributeError:
            messagebox.showerror("Remote Not Found", "No remote repository named 'origin' found.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")

    def call_groq_api(self, diff_text):
        """Call the Groq API to generate a commit message."""
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            messagebox.showerror("API Key Missing", "GROQ_API_KEY environment variable not set.")
            return None

        client = Groq(api_key=api_key)

        # Enhanced prompt to enforce Conventional Commit types
        prompt = (
            "You are an assistant that generates Git commit messages following the Conventional Commit specification. "
            "Based on the provided git diff, generate a concise commit message that starts with one of the following types "
            "followed by a colon and a space: feat, fix, docs, style, refactor, perf, test, chore, ci, build.\n\n"
            "Commit message should be only one line and should not contain any additional text or explanations.\n\n"
            "Example:\n"
            "feat: add user authentication module\n\n"
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
                model="llama3-8b-8192",  # Verify this is the correct model
            )
            commit_message = chat_completion.choices[0].message.content.strip()

            # Log the raw commit message for debugging
            logging.info(f"Raw commit message from API: '{commit_message}'")

            # Validate the commit message starts with a conventional type
            if any(commit_message.startswith(f"{ctype}:") for ctype in CONVENTIONAL_TYPES):
                logging.info("Commit message is valid.")
                return commit_message
            else:
                # Log the invalid commit message for debugging
                logging.warning(f"Invalid commit message received: '{commit_message}'")
                return None
        except GitCommandError as e:
            # Specific handling for context_length exceeded
            if "context_length exceeded" in str(e):
                messagebox.showerror(
                    "Groq API Error",
                    "The diff is too large for the Groq API to process. Please reduce the number of changes and try again."
                )
            else:
                messagebox.showerror("Groq API Error", f"An error occurred while calling the Groq API:\n{e}")
            return None
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
    parser.add_argument(
        '--push',
        action='store_true',
        help='Push the commit to the remote repository.'
    )
    args = parser.parse_args()

    try:
        repo = get_repo()
        changed_files = repo.index.diff(None)
        untracked_files = repo.untracked_files
        if not changed_files and not untracked_files:
            print("No changed files detected.")
            sys.exit(0)

        # Stage all changes
        repo.git.add(all=True)

        # Get the diff
        diff = repo.git.diff('--cached', '--pretty=format:')

        # Limit the diff size
        max_diff_size = 5000
        if len(diff) > max_diff_size:
            print(f"Warning: The diff is too large and has been truncated to {max_diff_size} characters.")
            diff = diff[:max_diff_size]

        # Call Groq API
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("Error: GROQ_API_KEY environment variable not set.")
            sys.exit(1)

        client = Groq(api_key=api_key)
        prompt = (
            "You are an assistant that generates Git commit messages following the Conventional Commit specification. "
            "Based on the provided git diff, generate a concise commit message that starts with one of the following types "
            "followed by a colon and a space: feat, fix, docs, style, refactor, perf, test, chore, ci, build.\n\n"
            "Commit message should be only one line and should not contain any additional text or explanations.\n\n"
            "Example:\n"
            "feat: add user authentication module\n\n"
            f"{diff}"
        )

        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama3-8b-8192",  # Verify this is the correct model
            )
            commit_message = chat_completion.choices[0].message.content.strip()

            # Log the raw commit message for debugging
            logging.info(f"Raw commit message from API: '{commit_message}'")

            # Validate the commit message starts with a conventional type
            if any(commit_message.startswith(f"{ctype}:") for ctype in CONVENTIONAL_TYPES):
                pass
            else:
                print("Error: The generated commit message does not start with a conventional commit type.")
                logging.warning(f"Invalid commit message received: '{commit_message}'")
                sys.exit(1)
        except GitCommandError as e:
            if "context_length exceeded" in str(e):
                print("Error: The diff is too large for the Groq API to process. Please reduce the number of changes and try again.")
            else:
                print(f"Groq API Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Groq API Error: {e}")
            sys.exit(1)

        if args.commit:
            repo.index.commit(commit_message)
            print("Commit created successfully.")
            if args.push:
                try:
                    origin = repo.remote(name='origin')
                    origin.push()
                    print("Pushed to remote repository successfully.")
                except GitCommandError as e:
                    print(f"Failed to push to remote repository:\n{e}")
                except AttributeError:
                    print("No remote repository named 'origin' found.")
                except Exception as e:
                    print(f"An unexpected error occurred while pushing:\n{e}")
        else:
            print("Generated Commit Message:")
            print(commit_message)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

def gui():
    """Graphical User Interface."""
    app = CommitGeneratorGUI()
    app.mainloop()

def main():
    parser = argparse.ArgumentParser(
        description="Auto-generate Git commit messages following Conventional Commits."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--cli', action='store_true', help='Launch CLI mode.')
    group.add_argument('--gui', action='store_true', help='Launch GUI mode.')
    args = parser.parse_args()

    if args.cli:
        cli()
    else:
        gui()

if __name__ == "__main__":
    main()

# Example of Desired Output:
# feat: Add LICENSE.txt file and CLI/GUI functionality for auto-generating Conventional Commit messages
