import argparse
import sys
import os
import re
from git import Repo, GitCommandError
import customtkinter as ctk
from tkinter import messagebox, scrolledtext, filedialog
import tkinter as tk
from groq import Groq
from dotenv import load_dotenv
import logging
import threading

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
    "perf", "test", "chore", "ci", "build",
    "rename", "remove"  # Added for handling renames and deletions
]

def is_valid_commit_message(commit_message):
    pattern = r'^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|rename|remove): .+'
    return re.match(pattern, commit_message) is not None

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

        # Spacer to push the status panel to the bottom
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        # Status Panel Frame
        self.status_panel = ctk.CTkFrame(self.sidebar_frame, corner_radius=0)
        self.status_panel.grid(row=7, column=0, padx=20, pady=10, sticky="s")

        # Groq Connection Status Label
        self.groq_status_label = ctk.CTkLabel(
            self.status_panel,
            text="Groq API: Disconnected",
            text_color="red",
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.groq_status_label.pack(fill="x", pady=(0, 5))

        # Diff Statistics Label
        self.diff_stats_label = ctk.CTkLabel(
            self.status_panel,
            text="Diff Size: 0 characters | Files Changed: 0",
            text_color="black",
            anchor="w",
            font=ctk.CTkFont(size=12)
        )
        self.diff_stats_label.pack(fill="x")

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

        # Initialize Groq API status
        self.update_groq_status(False)

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
            logging.error("Invalid scaling percentage selected.")

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
                logging.error(f"Selected directory is not a Git repository: {selected_dir}")
                return
            if self.set_repository(selected_dir):
                messagebox.showinfo("Repository Set", f"Repository set to:\n{selected_dir}")
                logging.info(f"Repository set to: {selected_dir}")
            else:
                self.prompt_repository_selection()

    def set_repository(self, path):
        """Set the current repository path and update the GUI."""
        try:
            # Enable rename detection using explicit flags
            repo = Repo(path)
            if repo.bare:
                messagebox.showerror("Git Repository Error", "Selected repository is bare. Please choose a valid Git repository.")
                logging.error(f"Selected repository is bare: {path}")
                return False
            self.repo = repo
            self.repo_path = path
            self.repo_path_display.configure(text=self.repo_path)
            logging.info(f"Repository path updated: {self.repo_path}")
            self.populate_files()
            self.enable_buttons()
            return True
        except Exception as e:
            messagebox.showerror("Git Repository Error", f"Failed to set repository:\n{e}")
            self.repo = None  # Ensure repo is set to None on failure
            self.disable_buttons()
            logging.error(f"Failed to set repository: {e}")
            return False

    def prompt_repository_selection(self):
        """Prompt the user to select a Git repository."""
        messagebox.showinfo("Select Repository", "Please select a Git repository to proceed.")
        logging.info("Prompting user to select a Git repository.")
        self.change_directory()

    def enable_buttons(self):
        """Enable commit, push, and refresh buttons."""
        self.generate_button.configure(state="normal")
        self.commit_button.configure(state="normal")
        self.push_button.configure(state="normal")
        self.refresh_button.configure(state="normal")
        logging.info("Enabled commit, push, and refresh buttons.")

    def disable_buttons(self):
        """Disable commit, push, and refresh buttons."""
        self.generate_button.configure(state="disabled")
        self.commit_button.configure(state="disabled")
        self.push_button.configure(state="disabled")
        self.refresh_button.configure(state="disabled")
        logging.info("Disabled commit, push, and refresh buttons.")

    def populate_files(self, max_files=50):
        """Populate the scrollable frame with changed files and checkboxes."""
        try:
            if not self.repo:
                # Repository is not set; prompt user to select a valid repository
                messagebox.showerror("Repository Error", "No valid Git repository selected.")
                logging.error("Attempted to populate files without a valid Git repository.")
                return

            # Retrieve changes with rename detection using explicit flags
            unstaged_diff = self.repo.git.diff('--name-status', '--find-renames')
            staged_diff = self.repo.git.diff('--name-status', 'HEAD', '--find-renames')
            untracked_files = self.repo.untracked_files

            # Parse the diffs
            changed_files = []

            # Parse staged diffs
            for line in staged_diff.splitlines():
                parts = line.split('\t')
                if len(parts) == 3 and parts[0].startswith('R'):
                    # Renamed files have the format 'R100\told_path\tnew_path'
                    _, old_path, new_path = parts
                    changed_files.append((f"{old_path} -> {new_path}", 'renamed'))
                elif len(parts) == 2:
                    status, path = parts
                    changed_files.append((path, 'staged'))

            # Parse unstaged diffs
            for line in unstaged_diff.splitlines():
                parts = line.split('\t')
                if len(parts) == 3 and parts[0].startswith('R'):
                    _, old_path, new_path = parts
                    changed_files.append((f"{old_path} -> {new_path}", 'renamed'))
                elif len(parts) == 2:
                    status, path = parts
                    changed_files.append((path, 'unstaged'))

            # Add untracked files
            for file_path in untracked_files:
                changed_files.append((file_path, 'untracked'))

            # Update Diff Statistics
            total_files = len(changed_files)
            total_diff_size = len(unstaged_diff) + len(staged_diff) + sum(len(f) for f in untracked_files)
            self.diff_stats_label.configure(text=f"Diff Size: {total_diff_size} characters | Files Changed: {total_files}")
            logging.info(f"Diff Size: {total_diff_size} characters | Files Changed: {total_files}")

            # Limit the number of displayed files
            if len(changed_files) > max_files:
                messagebox.showwarning(
                    "File Limit Reached",
                    f"Only the first {max_files} changed files are displayed. Please commit remaining changes separately."
                )
                logging.warning(f"Only displaying the first {max_files} changed files.")
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
                logging.info("No changes detected in the repository.")
                return

            for file_path, status in changed_files:
                var = tk.BooleanVar(value=True)
                display_text = f"{file_path} [{status}]"

                # Enhance UI with color indicators
                color = {
                    'renamed': "blue",
                    'remove': "red",
                    'staged': "green",
                    'unstaged': "yellow",
                    'untracked': "gray"
                }.get(status, "black")

                # Create a label with colored text instead of checkbox text
                frame = ctk.CTkFrame(self.scrollable_frame)
                frame.pack(anchor='w', padx=10, pady=2)

                chk = ctk.CTkCheckBox(
                    frame,
                    text="",
                    variable=var
                )
                chk.pack(side='left')

                label = ctk.CTkLabel(
                    frame,
                    text=display_text,
                    text_color=color
                )
                label.pack(side='left', padx=(5, 0))

                self.file_vars[file_path] = var
                logging.info(f"Added file to GUI: {display_text}")

        except AttributeError as e:
            messagebox.showerror("Error", f"Failed to retrieve changed files:\n{e}")
            logging.error(f"Failed to retrieve changed files: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve changed files:\n{e}")
            logging.error(f"Failed to retrieve changed files: {e}")

    def refresh_files(self):
        """Refresh the list of changed files."""
        self.populate_files()
        self.text_area.delete(1.0, tk.END)
        messagebox.showinfo("Refreshed", "File list has been refreshed.")
        logging.info("Refreshed the list of changed files.")

    def stage_selected_files(self):
        """Stage the selected files."""
        try:
            if not self.repo:
                messagebox.showerror("Repository Error", "No valid Git repository selected.")
                logging.error("No valid Git repository selected.")
                return False

            selected_files = [file for file, var in self.file_vars.items() if var.get()]
            if not selected_files:
                messagebox.showwarning("No Files Selected", "Please select at least one file to commit.")
                logging.warning("No files selected for staging.")
                return False

            logging.info(f"Selected files for staging: {selected_files}")

            for file in selected_files:
                if ' -> ' in file:
                    # Handle renamed files
                    old_path, new_path = file.split(' -> ')
                    logging.info(f"Renaming file from {old_path} to {new_path}")
                    self.repo.git.mv(old_path, new_path)
                    # After renaming, ensure the new file is staged
                    self.repo.index.add(new_path)
                    logging.info(f"Staged renamed file: {new_path}")
                else:
                    self.repo.index.add(file)
                    logging.info(f"Staged file: {file}")
            return True
        except GitCommandError as e:
            messagebox.showerror("Git Error", f"Failed to stage files:\n{e}")
            logging.error(f"Failed to stage files: {e}")
            return False
        except Exception as e:
            messagebox.showerror("Git Error", f"An unexpected error occurred while staging files:\n{e}")
            logging.error(f"Unexpected error during staging: {e}")
            return False

    def generate_message(self, max_retries=3):
        """Generate commit message using Groq AI based on selected changes."""
        logging.info("generate_message called.")
        if not self.stage_selected_files():
            logging.warning("Staging selected files failed or no files were staged.")
            return

        # Start a new thread for the API call to keep GUI responsive
        threading.Thread(target=self._generate_message_thread, args=(max_retries,)).start()

    def _generate_message_thread(self, max_retries):
        try:
            # Retrieve the staged diff with rename detection using explicit flags
            diff = self.repo.git.diff('--cached', '--pretty=format:', '--find-renames')
            limited_diff, was_truncated = self.limit_diff_size(diff, max_size=5000)

            logging.info(f"Retrieved staged diff ({len(diff)} characters).")
            if len(diff) == 0:
                logging.warning("Retrieved diff is empty. Please ensure that changes are staged correctly.")
                self.show_error("Empty Diff", "The staged changes diff is empty. Please ensure that changes are staged correctly.")
                return

            if was_truncated:
                self.show_warning("Diff Truncated", "The diff is too large and has been truncated to fit the API limits.")
                logging.warning("Diff was truncated due to size limitations.")

            for attempt in range(1, max_retries + 1):
                logging.info(f"Attempt {attempt} to generate commit message.")
                commit_message = self.call_groq_api(limited_diff)
                if commit_message:
                    logging.info("Commit message generated successfully.")
                    self.update_text_area(commit_message)
                    return  # Successful generation; exit the method
                else:
                    logging.warning(f"Attempt {attempt}: Failed to generate a valid commit message.")
                    if attempt < max_retries:
                        logging.info("Retrying to generate commit message...")
            # After max_retries attempts, allow manual input
            response = self.ask_yes_no(
                "Generate Commit Message",
                "Failed to generate a valid commit message after multiple attempts.\nWould you like to enter it manually?"
            )
            if response:
                self.clear_text_area()
                logging.info("User opted to enter commit message manually.")
                # The user can now type their commit message in the text area
        except Exception as e:
            self.show_error("Error", f"An error occurred:\n{e}")
            logging.error(f"Error during commit message generation: {e}")

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
            logging.info(f"Diff truncated: {was_truncated}")
            return limited_diff, was_truncated
        return diff_text, False

    def commit_message(self):
        """Commit the staged changes with the generated message."""
        if not self.repo:
            messagebox.showerror("Repository Error", "No valid Git repository selected.")
            logging.error("Attempted to commit without a valid Git repository.")
            return

        commit_msg = self.text_area.get(1.0, tk.END).strip()
        if not commit_msg:
            messagebox.showwarning("No Commit Message", "Please generate a commit message before committing.")
            logging.warning("Attempted to commit without a commit message.")
            return
        try:
            self.repo.index.commit(commit_msg)
            messagebox.showinfo("Success", "Commit created successfully.")
            logging.info("Commit created successfully.")
            self.populate_files()
            self.text_area.delete(1.0, tk.END)
            self.update_groq_status(False)  # Reset Groq status after commit
        except GitCommandError as e:
            messagebox.showerror("Git Error", f"Failed to create commit:\n{e}")
            logging.error(f"Failed to create commit: {e}")
        except Exception as e:
            messagebox.showerror("Git Error", f"An unexpected error occurred while creating commit:\n{e}")
            logging.error(f"Unexpected error during commit: {e}")

    def push_commit(self):
        """Push the latest commit to the remote repository."""
        if not self.repo:
            messagebox.showerror("Repository Error", "No valid Git repository selected.")
            logging.error("Attempted to push without a valid Git repository.")
            return

        try:
            origin = self.repo.remote(name='origin')
            origin.push()
            messagebox.showinfo("Success", "Pushed to remote repository successfully.")
            logging.info("Pushed to remote repository successfully.")
        except GitCommandError as e:
            messagebox.showerror("Push Error", f"Failed to push to remote repository:\n{e}")
            logging.error(f"Failed to push to remote repository: {e}")
        except AttributeError:
            messagebox.showerror("Remote Not Found", "No remote repository named 'origin' found.")
            logging.error("No remote repository named 'origin' found.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred while pushing:\n{e}")
            logging.error(f"An unexpected error occurred while pushing: {e}")

    def call_groq_api(self, diff_text):
        """Call the Groq API to generate a commit message."""
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            messagebox.showerror("API Key Missing", "GROQ_API_KEY environment variable not set.")
            logging.error("Groq API Key is missing.")
            self.update_groq_status(False)
            return None

        client = Groq(api_key=api_key)

        # Log the size of the diff before sending
        diff_size = len(diff_text)
        logging.info(f"Diff size: {diff_size} characters")

        # Update Diff Statistics in GUI
        self.diff_stats_label.configure(text=f"Diff Size: {diff_size} characters | Files Changed: {len(self.file_vars)}")
        logging.info(f"Updated Diff Statistics: Diff Size = {diff_size}, Files Changed = {len(self.file_vars)}")

        # Enhanced prompt to enforce Conventional Commit types, including renames and deletions
        prompt = (
            "Generate a single-line Git commit message following the Conventional Commit specification based on the provided git diff.\n\n"
            "Types: feat, fix, docs, style, refactor, perf, test, chore, ci, build, rename, remove.\n\n"
            "The commit message should start with the type, followed by a colon and a space, then a short description.\n\n"
            "Examples:\n"
            "feat: add user authentication module\n"
            "rename: move config file to config/settings.json\n"
            "remove: delete deprecated API endpoints\n\n"
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
                model="llama3-8b-8192",  # Correct model name as per Groq's documentation
            )
            commit_message = chat_completion.choices[0].message.content.strip()

            # Log the raw commit message for debugging
            logging.info(f"Raw commit message from API: '{commit_message}'")

            # Validate the commit message starts with a conventional type
            if is_valid_commit_message(commit_message):
                logging.info("Commit message is valid.")
                self.update_groq_status(True)
                # Optional: Display the commit message in the GUI
                return commit_message
            else:
                # Log the invalid commit message for debugging
                logging.warning(f"Invalid commit message received: '{commit_message}'")
                self.update_groq_status(False)
                return None
        except GitCommandError as e:
            # Specific handling for context_length exceeded
            if "context_length exceeded" in str(e):
                messagebox.showerror(
                    "Groq API Error",
                    "The diff is too large for the Groq API to process. Please reduce the number of changes and try again."
                )
                logging.error("Groq API Error: Context length exceeded.")
            else:
                messagebox.showerror("Groq API Error", f"An error occurred while calling the Groq API:\n{e}")
                logging.error(f"Groq API Error: {e}")
            self.update_groq_status(False)
            return None
        except Exception as e:
            messagebox.showerror("Groq API Error", f"An error occurred while calling the Groq API:\n{e}")
            logging.error(f"Groq API Error: {e}")
            self.update_groq_status(False)
            return None

    def update_groq_status(self, is_connected):
        """Update the Groq API connection status in the status panel."""
        if is_connected:
            self.groq_status_label.configure(text="Groq API: Connected", text_color="green")
            logging.info("Groq API status updated to Connected.")
        else:
            self.groq_status_label.configure(text="Groq API: Disconnected", text_color="red")
            logging.info("Groq API status updated to Disconnected.")

    # Implement thread-safe GUI updates
    def update_text_area(self, message):
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, message)
        logging.info("Updated commit message in GUI.")

    def clear_text_area(self):
        self.text_area.delete(1.0, tk.END)
        logging.info("Cleared commit message text area.")

    def show_warning(self, title, message):
        messagebox.showwarning(title, message)
        logging.warning(f"{title}: {message}")

    def show_error(self, title, message):
        messagebox.showerror(title, message)
        logging.error(f"{title}: {message}")

    def ask_yes_no(self, title, message):
        return messagebox.askyesno(title, message)

def get_repo():
    """Initialize and return the Git repository."""
    try:
        repo = Repo(os.getcwd(), search_parent_directories=True)
        if repo.bare:
            messagebox.showerror("Git Repository Error", "Repository is bare. Exiting.")
            logging.error("Repository is bare. Exiting.")
            sys.exit(1)
        return repo
    except Exception as e:
        messagebox.showerror("Git Repository Error", f"Error: {e}")
        logging.error(f"Git Repository Error: {e}")
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
        changed_files = repo.index.diff(None, rename=True)
        staged_changes = repo.index.diff("HEAD", rename=True)
        untracked_files = repo.untracked_files

        # Combine all changes to check if there are any changes
        if not changed_files and not staged_changes and not untracked_files:
            print("No changed files detected.")
            logging.info("No changed files detected.")
            sys.exit(0)

        # Stage all changes, including renames
        for item in staged_changes:
            if item.change_type == 'R':
                old_path, new_path = item.a_path, item.b_path
                logging.info(f"Staging renamed file from {old_path} to {new_path}")
                repo.git.mv(old_path, new_path)
            else:
                repo.git.add(item.a_path)
                logging.info(f"Staging file: {item.a_path}")
        for item in changed_files:
            if item.change_type == 'R':
                old_path, new_path = item.a_path, item.b_path
                logging.info(f"Staging renamed file from {old_path} to {new_path}")
                repo.git.mv(old_path, new_path)
            else:
                repo.git.add(item.a_path)
                logging.info(f"Staging file: {item.a_path}")
        for file_path in untracked_files:
            repo.git.add(file_path)
            logging.info(f"Staging untracked file: {file_path}")

        # Get the diff with rename detection using explicit flags
        diff = repo.git.diff('--cached', '--pretty=format:', '--find-renames')

        # Update Diff Statistics
        total_files = len(changed_files) + len(staged_changes) + len(untracked_files)
        total_diff_size = len(diff)
        logging.info(f"Diff Size: {total_diff_size} characters | Files Changed: {total_files}")

        # Limit the diff size
        max_diff_size = 5000
        if len(diff) > max_diff_size:
            print(f"Warning: The diff is too large and has been truncated to {max_diff_size} characters.")
            logging.warning(f"Diff is too large and has been truncated to {max_diff_size} characters.")
            diff = diff[:max_diff_size]

        # Call Groq API
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("Error: GROQ_API_KEY environment variable not set.")
            logging.error("Groq API Key is missing.")
            sys.exit(1)

        client = Groq(api_key=api_key)
        prompt = (
            "Generate a single-line Git commit message following the Conventional Commit specification based on the provided git diff.\n\n"
            "Types: feat, fix, docs, style, refactor, perf, test, chore, ci, build, rename, remove.\n\n"
            "The commit message should start with the type, followed by a colon and a space, then a short description.\n\n"
            "Examples:\n"
            "feat: add user authentication module\n"
            "rename: move config file to config/settings.json\n"
            "remove: delete deprecated API endpoints\n\n"
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
                model="llama3-8b-8192",  # Correct model name as per Groq's documentation
            )
            commit_message = chat_completion.choices[0].message.content.strip()
            print(commit_message)  # Correctly print the commit message
            logging.info(f"Raw commit message from API: '{commit_message}'")

            # Validate the commit message starts with a conventional type using regex
            if is_valid_commit_message(commit_message):
                pass  # Proceed as normal
            else:
                print("Error: The generated commit message does not start with a conventional commit type.")
                logging.warning(f"Invalid commit message received: '{commit_message}'")
                sys.exit(1)
        except GitCommandError as e:
            if "context_length exceeded" in str(e):
                print("Error: The diff is too large for the Groq API to process. Please reduce the number of changes and try again.")
                logging.error("Groq API Error: Context length exceeded.")
            else:
                print(f"Groq API Error: {e}")
                logging.error(f"Groq API Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Groq API Error: {e}")
            logging.error(f"Groq API Error: {e}")
            sys.exit(1)

        if args.commit:
            try:
                repo.index.commit(commit_message)
                print("Commit created successfully.")
                logging.info("Commit created successfully.")

                if args.push:
                    try:
                        origin = repo.remote(name='origin')
                        origin.push()
                        print("Pushed to remote repository successfully.")
                        logging.info("Pushed to remote repository successfully.")
                    except GitCommandError as e:
                        print(f"Failed to push to remote repository:\n{e}")
                        logging.error(f"Failed to push to remote repository: {e}")
                    except AttributeError:
                        print("No remote repository named 'origin' found.")
                        logging.error("No remote repository named 'origin' found.")
                    except Exception as e:
                        print(f"An unexpected error occurred while pushing:\n{e}")
                        logging.error(f"An unexpected error occurred while pushing: {e}")
            except GitCommandError as e:
                print(f"Failed to create commit:\n{e}")
                logging.error(f"Failed to create commit: {e}")
            except Exception as e:
                print(f"An unexpected error occurred while creating commit:\n{e}")
                logging.error(f"Unexpected error during commit: {e}")
        else:
            print("Generated Commit Message:")
            print(commit_message)
            logging.info(f"Generated Commit Message: {commit_message}")
    except:
        print("Exception occured")

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
