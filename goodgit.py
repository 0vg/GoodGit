"""
GoodGit: Automated Git commit message generator following Conventional Commit specifications.

Provides both Command-Line Interface (CLI) and Graphical User Interface (GUI) for generating
and managing Git commit messages using Groq AI.

Features:
- Select Git repository
- Display changed files with rename detection
- Generate commit messages via Groq AI
- Commit and push changes
"""

import argparse
import logging
import os
import re
import sys
import threading
import traceback
from typing import Tuple

from dotenv import load_dotenv
from git import GitCommandError, Repo
import customtkinter as ctk
from tkinter import filedialog, messagebox, scrolledtext
import tkinter as tk
from groq import Groq  # Ensure this is the correct Groq client

# Configure logging with rotation to prevent log files from growing indefinitely
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Increased verbosity for detailed logs

handler = RotatingFileHandler(
    'goodgit.log', maxBytes=5*1024*1024, backupCount=2
)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Load environment variables from .env file
load_dotenv()

# Conventional Commit Types
CONVENTIONAL_TYPES = [
    "feat", "fix", "docs", "style", "refactor",
    "perf", "test", "chore", "ci", "build",
    "rename", "remove"
]


def is_valid_commit_message(commit_message: str) -> bool:
    """
    Validate if the commit message follows the Conventional Commit specification.

    Args:
        commit_message (str): The commit message to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    pattern = r'^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|rename|remove): .+'
    return re.match(pattern, commit_message) is not None


class RepoManager:
    """
    Manages Git repository interactions.
    """
    def __init__(self, path: str):
        """
        Initialize the RepoManager with the given repository path.

        Args:
            path (str): The file system path to the Git repository.
        """
        self.repo_path = path
        logger.debug(f"Initializing RepoManager with path: {path}")
        self.repo = self.get_repo(path)

    @staticmethod
    def get_repo(path: str) -> Repo:
        """
        Initialize and return the Git repository.

        Args:
            path (str): The file system path to the Git repository.

        Returns:
            Repo: An instance of the Git repository.

        Raises:
            GitCommandError: If the repository is bare.
            Exception: For any other errors during repository initialization.
        """
        try:
            logger.debug(f"Current Working Directory: {os.getcwd()}")
            repo = Repo(path, search_parent_directories=True)
            if repo.bare:
                logger.error("Selected repository is bare: %s", path)
                raise GitCommandError("Repository is bare.", 1)
            logger.info("Repository initialized at path: %s", path)
            return repo
        except GitCommandError as e:
            logger.error("GitCommandError: %s", e)
            raise
        except Exception as e:
            logger.error("Error initializing repository: %s", e)
            raise

    def get_changed_files(self) -> Tuple[list, list, list]:
        """
        Retrieve changed, staged, and untracked files.

        Returns:
            Tuple[list, list, list]: A tuple containing lists of changed_files, staged_changes, and untracked_files.
        """
        try:
            # Use rename=True to enable rename detection with -M
            changed_files = self.repo.index.diff(None)
            staged_changes = self.repo.index.diff("HEAD")
            untracked_files = self.repo.untracked_files
            logger.info("Retrieved changed files: %d, staged changes: %d, untracked files: %d",
                        len(changed_files), len(staged_changes), len(untracked_files))
            return list(changed_files), list(staged_changes), untracked_files
        except GitCommandError as e:
            logger.error("Failed to retrieve changed files: %s", e, exc_info=True)
            raise
        except Exception as e:
            logger.error("Unexpected error retrieving changed files: %s", e, exc_info=True)
            raise

    def unstage_all_files(self) -> bool:
        """
        Unstage all currently staged files.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self.repo.git.reset()
            logger.info("All files have been unstaged.")
            return True
        except GitCommandError as e:
            logger.error("Failed to unstage all files: %s", e)
            messagebox.showerror("Git Error", f"Failed to unstage all files:\n{e}")
            return False
        except Exception as e:
            logger.error("Unexpected error during unstaging: %s", traceback.format_exc())
            messagebox.showerror("Git Error", f"An unexpected error occurred while unstaging files:\n{e}")
            return False

    def stage_files(self, selected_files: list) -> bool:
        """
        Stage the selected files for commit.

        Args:
            selected_files (list): List of file paths selected to be staged.

        Returns:
            bool: True if staging was successful, False otherwise.
        """
        try:
            for file in selected_files:
                if ' -> ' in file:
                    old_path, new_path = file.split(' -> ')
                    logger.info("Renaming file from %s to %s", old_path, new_path)
                    self.repo.git.mv(old_path, new_path)
                    self.repo.index.add(new_path)
                    logger.info("Staged renamed file: %s", new_path)
                else:
                    self.repo.index.add(file)
                    logger.info("Staged file: %s", file)
            return True
        except GitCommandError as e:
            logger.error("Failed to stage files: %s", e)
            messagebox.showerror("Git Error", f"Failed to stage files:\n{e}")
            return False
        except Exception as e:
            logger.error("Unexpected error during staging: %s", traceback.format_exc())
            messagebox.showerror("Git Error", f"An unexpected error occurred while staging files:\n{e}")
            return False

    def commit_changes(self, commit_message: str) -> bool:
        """
        Commit the staged changes with the provided commit message.

        Args:
            commit_message (str): The commit message.

        Returns:
            bool: True if commit was successful, False otherwise.
        """
        try:
            self.repo.index.commit(commit_message)
            logger.info("Commit created with message: %s", commit_message)
            messagebox.showinfo("Success", "Commit created successfully.")
            return True
        except GitCommandError as e:
            logger.error("Failed to create commit: %s", e)
            messagebox.showerror("Git Error", f"Failed to create commit:\n{e}")
            return False
        except Exception as e:
            logger.error("Unexpected error during commit: %s", traceback.format_exc())
            messagebox.showerror("Git Error", f"An unexpected error occurred while creating commit:\n{e}")
            return False

    def push_changes(self) -> bool:
        """
        Push the latest commit to the remote repository.

        Returns:
            bool: True if push was successful, False otherwise.
        """
        try:
            origin = self.repo.remote(name='origin')
            origin.push()
            logger.info("Pushed changes to remote repository.")
            messagebox.showinfo("Success", "Pushed to remote repository successfully.")
            return True
        except GitCommandError as e:
            logger.error("Failed to push to remote repository: %s", e)
            messagebox.showerror("Push Error", f"Failed to push to remote repository:\n{e}")
            return False
        except AttributeError:
            logger.error("No remote repository named 'origin' found.")
            messagebox.showerror("Remote Not Found", "No remote repository named 'origin' found.")
            return False
        except Exception as e:
            logger.error("Unexpected error during push: %s", traceback.format_exc())
            messagebox.showerror("Error", f"An unexpected error occurred while pushing:\n{e}")
            return False

    def get_staged_diff(self) -> Tuple[str, bool]:
        """
        Get the staged diff with rename detection.

        Returns:
            Tuple[str, bool]: The staged diff text and a boolean indicating if it was truncated.
        """
        try:
            # Use only one rename detection flag to avoid conflicts
            git_command = ['git', 'diff', '--cached', '--pretty=format:', '-M']
            logger.debug(f"Executing git command: {' '.join(git_command)}")
            diff_text = self.repo.git.diff('--cached', '--pretty=format:', '-M')  # Using -M
            limited_diff, was_truncated = self.limit_diff_size(diff_text, max_size=3000)
            logger.info("Retrieved staged diff (%d characters). Truncated: %s", len(limited_diff), was_truncated)
            return limited_diff, was_truncated
        except GitCommandError as e:
            logger.error("Failed to retrieve staged diff: %s", e)
            messagebox.showerror("Git Error", f"Failed to retrieve staged diff:\n{e}")
            return "", False
        except Exception as e:
            logger.error("Unexpected error retrieving staged diff: %s", traceback.format_exc())
            messagebox.showerror("Error", f"An unexpected error occurred while retrieving staged diff:\n{e}")
            return "", False

    @staticmethod
    def limit_diff_size(diff_text: str, max_size: int = 3000) -> Tuple[str, bool]:
        """
        Limits the size of the diff_text to max_size characters.

        Args:
            diff_text (str): The full diff text.
            max_size (int): The maximum allowed size in characters.

        Returns:
            Tuple[str, bool]: The limited diff text and a boolean indicating if it was truncated.
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
            logger.info("Diff truncated: %s", was_truncated)
            return limited_diff, was_truncated
        return diff_text, False


class APIManager:
    """
    Manages interactions with the Groq API.
    """
    def __init__(self, api_key: str):
        """
        Initialize the APIManager with the provided API key.

        Args:
            api_key (str): The Groq API key.
        """
        self.api_key = api_key
        self.client = self.initialize_client()

    def initialize_client(self) -> Groq:
        """
        Initialize the Groq API client.

        Returns:
            Groq: The initialized Groq API client.

        Raises:
            Exception: If initialization fails.
        """
        try:
            client = Groq(api_key=self.api_key)
            logger.info("Groq API client initialized.")
            return client
        except Exception as e:
            logger.error("Failed to initialize Groq API client: %s", e)
            raise

    def generate_commit_message(self, diff_text: str) -> str:
        """
        Generate a commit message based on the provided diff using the Groq API.

        Args:
            diff_text (str): The git diff text.

        Returns:
            str: The generated commit message, or an empty string if generation failed.
        """
        prompt = (
            "Generate a single-line Git commit message following the Conventional Commit specification "
            "based on the provided git diff.\n\n"
            "Types: feat, fix, docs, style, refactor, perf, test, chore, ci, build, rename, remove.\n\n"
            "The commit message should start with the type, followed by a colon and a space, then a short description.\n\n"
            "Examples:\n"
            "feat: add user authentication module\n"
            "rename: move config file to config/settings.json\n"
            "remove: delete deprecated API endpoints\n\n"
            f"{diff_text}"
        )
        try:
            logger.debug("Sending prompt to Groq API.")
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama3-groq-8b-8192-tool-use-preview",  # Updated to a supported Groq model
            )
            logger.debug("Received response from Groq API.")
            if not chat_completion.choices:
                logger.error("No choices returned from Groq API.")
                return ""
            commit_message = chat_completion.choices[0].message.content.strip()
            logger.info("Commit message received from API: %s", commit_message)
            return commit_message
        except GitCommandError as e:
            if "context_length exceeded" in str(e):
                logger.error("Groq API Error: Context length exceeded.")
                messagebox.showerror(
                    "Groq API Error",
                    "The diff is too large for the Groq API to process. Please reduce the number of changes and try again."
                )
            else:
                logger.error("Groq API Error: %s", e)
                messagebox.showerror("Groq API Error", f"An error occurred while calling the Groq API:\n{e}")
            return ""
        except Exception as e:
            logger.error("Groq API Error: %s", traceback.format_exc())
            messagebox.showerror("Groq API Error", f"An error occurred while calling the Groq API:\n{e}")
            return ""

    def close_client(self):
        """
        Close the Groq API client connection if necessary.
        """
        # Assuming Groq client has a close method; otherwise, this can be omitted
        try:
            self.client.close()
            logger.info("Groq API client closed.")
        except AttributeError:
            # If no close method exists, do nothing
            pass
        except Exception as e:
            logger.error("Error closing Groq API client: %s", traceback.format_exc())


class CommitGeneratorGUI(ctk.CTk):
    """
    Graphical User Interface for the GoodGit application.
    """
    def __init__(self):
        super().__init__()

        self.repo_manager = None
        self.api_manager = None
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

        # Test Diff Button for debugging
        self.test_diff_button = ctk.CTkButton(
            self.main_frame,
            text="🔍 Test Git Diff",
            command=self.test_git_diff_gui,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.test_diff_button.grid(row=6, column=0, columnspan=2, pady=10, sticky="ew")

        # Attempt to set the default repository path to current directory
        self.repo_path = os.getcwd()
        try:
            repo = Repo(self.repo_path, search_parent_directories=True)
            repo_root = repo.working_tree_dir
            self.repo_manager = RepoManager(repo_root)
            self.repo_path_display.configure(text=repo_root)
            self.populate_files()
            self.enable_buttons()
            logger.info("Repository set to: %s", repo_root)
        except GitCommandError:
            self.prompt_repository_selection()
        except Exception as e:
            logger.error("Error setting repository: %s", traceback.format_exc())
            messagebox.showerror("Repository Error", f"An error occurred while setting the repository:\n{e}")

        # Initialize Groq API status
        self.update_groq_status(False)

        # Initialize APIManager if GROQ_API_KEY is set
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            try:
                self.api_manager = APIManager(api_key=api_key)
                self.update_groq_status(True)
            except Exception:
                self.update_groq_status(False)
        else:
            logger.error("GROQ_API_KEY environment variable not set.")
            messagebox.showerror("API Key Missing", "GROQ_API_KEY environment variable not set.")

        # Apply initial theme to ScrolledText and ScrollableFrame
        self.update_scrolledtext_colors()
        self.update_scrollable_frame_colors()

    def _get_text_area_bg(self) -> str:
        """
        Get the background color for the ScrolledText based on the current theme.

        Returns:
            str: The background color hex code.
        """
        mode = ctk.get_appearance_mode()
        return "#2B2B2B" if mode == "Dark" else "#FFFFFF"

    def _get_text_area_fg(self) -> str:
        """
        Get the foreground color for the ScrolledText based on the current theme.

        Returns:
            str: The foreground color hex code.
        """
        mode = ctk.get_appearance_mode()
        return "#FFFFFF" if mode == "Dark" else "#000000"

    def _get_scrollable_frame_bg(self) -> str:
        """
        Get the background color for the ScrollableFrame based on the current theme.

        Returns:
            str: The background color hex code.
        """
        mode = ctk.get_appearance_mode()
        return "#2B2B2B" if mode == "Dark" else "#FFFFFF"

    def change_appearance_mode_event(self, new_appearance_mode: str):
        """
        Change the appearance mode of the application.

        Args:
            new_appearance_mode (str): The new appearance mode ("Light", "Dark", "System").
        """
        ctk.set_appearance_mode(new_appearance_mode)
        self.update_scrolledtext_colors()
        self.update_scrollable_frame_colors()
        logger.info("Changed appearance mode to: %s", new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        """
        Change the scaling of the application.

        Args:
            new_scaling (str): The new scaling percentage (e.g., "100%").
        """
        try:
            new_scaling_float = int(new_scaling.replace("%", "")) / 100
            ctk.set_widget_scaling(new_scaling_float)
            logger.info("Changed UI scaling to: %s", new_scaling)
        except ValueError:
            messagebox.showerror("Invalid Scaling", "Please select a valid scaling percentage.")
            logger.error("Invalid scaling percentage selected: %s", new_scaling)

    def update_scrolledtext_colors(self):
        """
        Update the ScrolledText widget colors based on the current appearance mode.
        """
        self.text_area.configure(
            bg=self._get_text_area_bg(),
            fg=self._get_text_area_fg(),
            insertbackground=self._get_text_area_fg()
        )
        logger.info("Updated ScrolledText colors based on theme.")

    def update_scrollable_frame_colors(self):
        """
        Update the ScrollableFrame colors based on the current theme.
        """
        bg_color = self._get_scrollable_frame_bg()
        self.scrollable_frame.configure(fg_color=bg_color)
        logger.info("Updated ScrollableFrame colors based on theme.")

    def change_directory(self):
        """
        Open a dialog to select a new Git repository directory.
        """
        selected_dir = filedialog.askdirectory()
        if selected_dir:
            try:
                # Attempt to initialize Repo with search_parent_directories=True
                repo = Repo(selected_dir, search_parent_directories=True)
                repo_root = repo.working_tree_dir
                logger.info("Repository found at: %s", repo_root)

                self.repo_manager = RepoManager(repo_root)
                self.repo_path = repo_root
                self.repo_path_display.configure(text=self.repo_path)
                self.populate_files()
                self.enable_buttons()
                logger.info("Repository set to: %s", self.repo_path)
            except GitCommandError:
                messagebox.showerror("Invalid Repository", "The selected directory is not within a Git repository.")
                logger.error("Selected directory is not within a Git repository: %s", selected_dir)
                self.disable_buttons()
            except Exception as e:
                logger.error("Error setting repository: %s", traceback.format_exc())
                messagebox.showerror("Repository Error", f"An error occurred while setting the repository:\n{e}")
                self.disable_buttons()

    def set_repository(self, path: str) -> bool:
        """
        Set the current repository path and update the GUI.

        Args:
            path (str): The file system path to the Git repository.

        Returns:
            bool: True if repository was set successfully, False otherwise.
        """
        try:
            self.repo_manager = RepoManager(path)
            self.repo_path = path
            self.repo_path_display.configure(text=self.repo_path)
            self.populate_files()
            self.enable_buttons()
            logger.info("Repository set to: %s", self.repo_path)
            return True
        except GitCommandError as e:
            messagebox.showerror("Git Repository Error", f"Repository is bare or invalid:\n{e}")
            logger.error("Failed to set repository: %s", e)
            self.disable_buttons()
            return False
        except Exception as e:
            logger.error("Error setting repository: %s", traceback.format_exc())
            messagebox.showerror("Repository Error", f"An error occurred while setting the repository:\n{e}")
            self.disable_buttons()
            return False

    def prompt_repository_selection(self):
        """
        Prompt the user to select a Git repository.
        """
        messagebox.showinfo("Select Repository", "Please select a Git repository to proceed.")
        logger.info("Prompting user to select a Git repository.")
        self.change_directory()

    def enable_buttons(self):
        """
        Enable commit, push, and refresh buttons.
        """
        self.generate_button.configure(state="normal")
        self.commit_button.configure(state="normal")
        self.push_button.configure(state="normal")
        self.refresh_button.configure(state="normal")
        logger.info("Enabled commit, push, and refresh buttons.")

    def disable_buttons(self):
        """
        Disable commit, push, and refresh buttons.
        """
        self.generate_button.configure(state="disabled")
        self.commit_button.configure(state="disabled")
        self.push_button.configure(state="disabled")
        self.refresh_button.configure(state="disabled")
        logger.info("Disabled commit, push, and refresh buttons.")

    def populate_files(self, max_files: int = 50):
        """
        Populate the scrollable frame with changed files and checkboxes.

        Args:
            max_files (int, optional): Maximum number of files to display. Defaults to 50.
        """
        try:
            changed_files, staged_changes, untracked_files = self.repo_manager.get_changed_files()

            # Parse the diffs
            changed_files_list = []

            # Parse staged diffs
            for item in staged_changes:
                if item.change_type == 'R':
                    old_path, new_path = item.a_path, item.b_path
                    changed_files_list.append((f"{old_path} -> {new_path}", 'renamed'))
                else:
                    changed_files_list.append((item.a_path, 'staged'))

            # Parse unstaged diffs
            for item in changed_files:
                if item.change_type == 'R':
                    old_path, new_path = item.a_path, item.b_path
                    changed_files_list.append((f"{old_path} -> {new_path}", 'renamed'))
                else:
                    changed_files_list.append((item.a_path, 'unstaged'))

            # Add untracked files
            for file_path in untracked_files:
                changed_files_list.append((file_path, 'untracked'))

            total_files = len(changed_files_list)
            try:
                staged_diff = self.repo_manager.repo.git.diff('--cached', '--pretty=format:', '-M')
                unstaged_diff = self.repo_manager.repo.git.diff('--name-status', '-M')
                untracked_diff = ''.join(untracked_files)  # Approximation
                total_diff_size = len(staged_diff) + len(unstaged_diff) + sum(len(f) for f in untracked_files)
            except GitCommandError as e:
                logger.error("Error calculating diff size: %s", e)
                total_diff_size = 0

            self.diff_stats_label.configure(text=f"Diff Size: {total_diff_size} characters | Files Changed: {total_files}")
            logger.info("Diff Size: %d characters | Files Changed: %d", total_diff_size, total_files)

            # Limit the number of displayed files
            if total_files > max_files:
                messagebox.showwarning(
                    "File Limit Reached",
                    f"Only the first {max_files} changed files are displayed. Please commit remaining changes separately."
                )
                logger.warning("Only displaying the first %d changed files.", max_files)
                changed_files_list = changed_files_list[:max_files]

            # Clear previous checkboxes
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            self.file_vars.clear()

            if not changed_files_list:
                no_changes_label = ctk.CTkLabel(
                    self.scrollable_frame,
                    text="No changes detected.",
                    fg_color=("red", "#FFCCCC"),
                    text_color="black"
                )
                no_changes_label.pack(pady=10, padx=10, fill="x")
                logger.info("No changes detected in the repository.")
                return

            for file_path, status in changed_files_list:
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
                logger.info("Added file to GUI: %s", display_text)

        except Exception as e:
            logger.error("Failed to populate files: %s", traceback.format_exc())
            messagebox.showerror("Error", f"Failed to retrieve changed files:\n{e}")

    def refresh_files(self):
        """
        Refresh the list of changed files and clear the commit message text area.
        """
        self.populate_files()
        self.text_area.delete(1.0, tk.END)
        messagebox.showinfo("Refreshed", "File list has been refreshed.")
        logger.info("Refreshed the list of changed files.")

    def stage_selected_files(self) -> bool:
        """
        Unstage all files and then stage the selected files for commit.

        Returns:
            bool: True if staging was successful, False otherwise.
        """
        try:
            # Unstage all files first to ensure only selected files are staged
            if not self.repo_manager.unstage_all_files():
                return False

            selected_files = [file for file, var in self.file_vars.items() if var.get()]
            if not selected_files:
                messagebox.showwarning("No Files Selected", "Please select at least one file to commit.")
                logger.warning("No files selected for staging.")
                return False

            logger.info("Selected files for staging: %s", selected_files)
            return self.repo_manager.stage_files(selected_files)
        except Exception as e:
            logger.error("Error in stage_selected_files: %s", traceback.format_exc())
            messagebox.showerror("Error", f"An unexpected error occurred while staging files:\n{e}")
            return False

    def generate_message(self, max_retries: int = 3):
        """
        Generate commit message using Groq AI based on selected changes.

        Args:
            max_retries (int, optional): Maximum number of retries for message generation. Defaults to 3.
        """
        logger.info("Generate message button clicked.")
        if not self.stage_selected_files():
            logger.warning("Staging selected files failed or no files were staged.")
            return

        # Start a new thread for the API call to keep GUI responsive
        threading.Thread(target=self._generate_message_thread, args=(max_retries,), daemon=True).start()

    def _generate_message_thread(self, max_retries: int):
        """
        Threaded method to generate commit message.

        Args:
            max_retries (int): Number of retry attempts.
        """
        try:
            logger.info("Starting commit message generation thread.")
            diff_text, was_truncated = self.repo_manager.get_staged_diff()
            logger.debug("Diff Text Length: %d, Truncated: %s", len(diff_text), was_truncated)
            if not diff_text:
                logger.warning("No diff text available for commit message generation.")
                return

            if was_truncated:
                self.show_warning("Diff Truncated",
                                   "The diff is too large and has been truncated to fit the API limits.")
                logger.warning("Diff was truncated due to size limitations.")

            # Always generate commit message via API regardless of number of files

            for attempt in range(1, max_retries + 1):
                logger.info("Attempt %d to generate commit message.", attempt)
                commit_message = self.api_manager.generate_commit_message(diff_text)
                logger.debug("Commit Message Attempt %d: %s", attempt, commit_message)
                if commit_message and is_valid_commit_message(commit_message):
                    logger.info("Commit message generated successfully on attempt %d.", attempt)
                    self.update_text_area(commit_message)
                    return
                else:
                    logger.warning("Attempt %d: Failed to generate a valid commit message.", attempt)
                    if attempt < max_retries:
                        logger.info("Retrying to generate commit message...")
            # After max_retries attempts, allow manual input
            response = self.ask_yes_no(
                "Generate Commit Message",
                "Failed to generate a valid commit message after multiple attempts.\nWould you like to enter it manually?"
            )
            if response:
                self.clear_text_area()
                logger.info("User opted to enter commit message manually.")
        except Exception as e:
            logger.error("Error during commit message generation: %s", traceback.format_exc())
            self.show_error("Error", f"An error occurred:\n{e}")

    def commit_message(self):
        """
        Commit the staged changes with the generated or manually entered commit message.
        """
        logger.info("Commit button clicked.")
        if not self.repo_manager:
            messagebox.showerror("Repository Error", "No valid Git repository selected.")
            logger.error("No valid Git repository selected.")
            return

        commit_msg = self.text_area.get(1.0, tk.END).strip()
        if not commit_msg:
            messagebox.showwarning("No Commit Message", "Please generate a commit message before committing.")
            logger.warning("Attempted to commit without a commit message.")
            return

        success = self.repo_manager.commit_changes(commit_msg)
        if success:
            self.populate_files()
            self.text_area.delete(1.0, tk.END)
            self.update_groq_status(False)  # Reset Groq status after commit

    def push_commit(self):
        """
        Push the latest commit to the remote repository.
        """
        logger.info("Push button clicked.")
        if not self.repo_manager:
            messagebox.showerror("Repository Error", "No valid Git repository selected.")
            logger.error("No valid Git repository selected.")
            return

        success = self.repo_manager.push_changes()
        if success:
            logger.info("Changes pushed successfully.")

    def call_groq_api(self, diff_text: str) -> str:
        """
        Call the Groq API to generate a commit message.

        Args:
            diff_text (str): The git diff text.

        Returns:
            str: The generated commit message, or empty string if failed.
        """
        if not self.api_manager:
            logger.error("API Manager not initialized.")
            messagebox.showerror("API Error", "Groq API is not initialized.")
            return ""

        commit_message = self.api_manager.generate_commit_message(diff_text)
        if commit_message and is_valid_commit_message(commit_message):
            logger.info("Commit message is valid: %s", commit_message)
            self.update_groq_status(True)
            return commit_message
        else:
            logger.warning("Invalid commit message received: %s", commit_message)
            self.update_groq_status(False)
            return ""

    def update_groq_status(self, is_connected: bool):
        """
        Update the Groq API connection status in the status panel.

        Args:
            is_connected (bool): Connection status.
        """
        if is_connected:
            self.groq_status_label.configure(text="Groq API: Connected", text_color="green")
            logger.info("Groq API status updated to Connected.")
        else:
            self.groq_status_label.configure(text="Groq API: Disconnected", text_color="red")
            logger.info("Groq API status updated to Disconnected.")

    def update_text_area(self, message: str):
        """
        Update the commit message text area with the generated message.

        Args:
            message (str): The commit message to display.
        """
        self.text_area.after(0, lambda: self.text_area.delete(1.0, tk.END))
        self.text_area.after(0, lambda: self.text_area.insert(tk.END, message))
        logger.info("Updated commit message in GUI.")

    def clear_text_area(self):
        """
        Clear the commit message text area.
        """
        self.text_area.after(0, lambda: self.text_area.delete(1.0, tk.END))
        logger.info("Cleared commit message text area.")

    def show_warning(self, title: str, message: str):
        """
        Show a warning message box.

        Args:
            title (str): The title of the warning.
            message (str): The warning message.
        """
        self.text_area.after(0, lambda: messagebox.showwarning(title, message))
        logger.warning("%s: %s", title, message)

    def show_error(self, title: str, message: str):
        """
        Show an error message box.

        Args:
            title (str): The title of the error.
            message (str): The error message.
        """
        self.text_area.after(0, lambda: messagebox.showerror(title, message))
        logger.error("%s: %s", title, message)

    def ask_yes_no(self, title: str, message: str) -> bool:
        """
        Prompt the user with a Yes/No question.

        Args:
            title (str): The title of the prompt.
            message (str): The prompt message.

        Returns:
            bool: True if user selects Yes, False otherwise.
        """
        return messagebox.askyesno(title, message)

    def test_git_diff_gui(self):
        """
        A test function to run git diff and display the result.
        """
        try:
            diff_text, was_truncated = self.repo_manager.get_staged_diff()
            if was_truncated:
                messagebox.showwarning("Diff Truncated", "The diff was truncated to fit API limits.")
            # Display the diff in a message box or print to console
            messagebox.showinfo("Staged Diff", diff_text)
            logger.debug("Staged Diff:\n%s", diff_text)
        except Exception as e:
            logger.error("Error in test_git_diff_gui: %s", traceback.format_exc())
            messagebox.showerror("Error", f"An error occurred during test git diff:\n{e}")


def test_git_diff(repo_path: str):
    """
    Minimal test to verify git diff command using GitPython.

    Args:
        repo_path (str): Path to the Git repository.
    """
    try:
        repo = Repo(repo_path, search_parent_directories=True)
        if repo.bare:
            logger.error("Repository is bare.")
            print("Repository is bare.")
            return
        # Use only one flag: -M or --find-renames
        git_command = ['git', 'diff', '--cached', '--pretty=format:', '-M']
        logger.debug(f"Executing git command: {' '.join(git_command)}")
        diff_text = repo.git.diff('--cached', '--pretty=format:', '-M')  # Using -M
        print("Diff Output:")
        print(diff_text)
    except GitCommandError as e:
        logger.error("GitCommandError: %s", e)
        print(f"GitCommandError: {e}")
    except Exception as e:
        logger.error("Exception: %s", traceback.format_exc())
        print(f"Exception: {e}")


def cli():
    """
    Command-Line Interface for the GoodGit application.
    """
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
    parser.add_argument(
        '--test-diff',
        action='store_true',
        help='Run a minimal git diff test.'
    )
    args = parser.parse_args()

    if args.test_diff:
        repo_path = os.getcwd()
        test_git_diff(repo_path)
        sys.exit(0)

    try:
        repo_manager = RepoManager(os.getcwd())

        changed_files, staged_changes, untracked_files = repo_manager.get_changed_files()

        # Combine all changes to check if there are any changes
        if not changed_files and not staged_changes and not untracked_files:
            logger.info("No changed files detected.")
            sys.exit(0)

        # Stage all changes, including renames
        # Collect all files to stage
        files_to_stage = []

        for item in staged_changes:
            if item.change_type == 'R':
                old_path, new_path = item.a_path, item.b_path
                logger.info("Staging renamed file from %s to %s", old_path, new_path)
                files_to_stage.append(f"{old_path} -> {new_path}")
            else:
                files_to_stage.append(item.a_path)

        for item in changed_files:
            if item.change_type == 'R':
                old_path, new_path = item.a_path, item.b_path
                logger.info("Staging renamed file from %s to %s", old_path, new_path)
                files_to_stage.append(f"{old_path} -> {new_path}")
            else:
                files_to_stage.append(item.a_path)

        for file_path in untracked_files:
            files_to_stage.append(file_path)
            logger.info("Staging untracked file: %s", file_path)

        if not repo_manager.stage_files(files_to_stage):
            sys.exit(1)

        # Get the diff with rename detection using explicit flags
        git_command = ['git', 'diff', '--cached', '--pretty=format:', '-M']
        logger.debug(f"Executing git command: {' '.join(git_command)}")
        diff = repo_manager.repo.git.diff('--cached', '--pretty=format:', '-M')  # Using -M

        # Update Diff Statistics
        try:
            staged_diff = repo_manager.repo.git.diff('--cached', '--pretty=format:', '-M')
            unstaged_diff = repo_manager.repo.git.diff('--name-status', '-M')
            untracked_diff = ''.join(untracked_files)  # Approximation
            total_diff_size = len(staged_diff) + len(unstaged_diff) + sum(len(f) for f in untracked_files)
        except GitCommandError as e:
            logger.error("Error calculating diff size: %s", e)
            total_diff_size = 0

        total_files = len(changed_files) + len(staged_changes) + len(untracked_files)
        logger.info("Diff Size: %d characters | Files Changed: %d", total_diff_size, total_files)

        # Limit the diff size
        max_diff_size = 5000
        if len(diff) > max_diff_size:
            logger.warning("Diff is too large and has been truncated to %d characters.", max_diff_size)
            diff = diff[:max_diff_size]

        # Call Groq API
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            logger.error("Groq API Key is missing.")
            sys.exit(1)

        api_manager = APIManager(api_key=api_key)
        prompt = (
            "Generate a single-line Git commit message following the Conventional Commit specification "
            "based on the provided git diff.\n\n"
            "Types: feat, fix, docs, style, refactor, perf, test, chore, ci, build, rename, remove.\n\n"
            "The commit message should start with the type, followed by a colon and a space, then a short description.\n\n"
            "Examples:\n"
            "feat: add user authentication module\n"
            "rename: move config file to config/settings.json\n"
            "remove: delete deprecated API endpoints\n\n"
            f"{diff}"
        )

        try:
            commit_message = api_manager.generate_commit_message(diff)
            logger.info("Generated commit message: %s", commit_message)

            # Validate the commit message
            if is_valid_commit_message(commit_message):
                pass  # Proceed as normal
            else:
                logger.warning("Invalid commit message received: %s", commit_message)
                sys.exit(1)
        except GitCommandError as e:
            if "context_length exceeded" in str(e):
                logger.error("Groq API Error: Context length exceeded.")
            else:
                logger.error("Groq API Error: %s", e)
            sys.exit(1)
        except Exception as e:
            logger.error("Groq API Error: %s", traceback.format_exc())
            sys.exit(1)

        if args.commit:
            try:
                repo_manager.commit_changes(commit_message)
                logger.info("Commit created successfully.")

                if args.push:
                    try:
                        repo_manager.push_changes()
                        logger.info("Pushed to remote repository successfully.")
                    except GitCommandError as e:
                        logger.error("Failed to push to remote repository: %s", e)
                    except AttributeError:
                        logger.error("No remote repository named 'origin' found.")
                    except Exception as e:
                        logger.error("An unexpected error occurred while pushing: %s", traceback.format_exc())
            except GitCommandError as e:
                logger.error("Failed to create commit: %s", e)
            except Exception as e:
                logger.error("Unexpected error during commit: %s", traceback.format_exc())
        else:
            logger.info("Generated Commit Message: %s", commit_message)
            print("Generated Commit Message:")
            print(commit_message)
    except Exception as e:
        logger.error("Unhandled Exception: %s", traceback.format_exc())
        sys.exit(1)


def gui():
    """
    Launch the Graphical User Interface.
    """
    app = CommitGeneratorGUI()
    app.mainloop()


def main():
    """
    Main function to parse arguments and launch the appropriate interface.
    """
    parser = argparse.ArgumentParser(
        description="Auto-generate Git commit messages following Conventional Commits."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--cli', action='store_true', help='Launch CLI mode.')
    group.add_argument('--gui', action='store_true', help='Launch GUI mode.')
    group.add_argument('--test-diff', action='store_true', help='Run a minimal git diff test.')
    args = parser.parse_args()

    if args.cli:
        cli()
    elif args.gui:
        gui()
    elif args.test_diff:
        repo_path = os.getcwd()
        test_git_diff(repo_path)
    else:
        gui()


def test_git_diff(repo_path: str):
    """
    Minimal test to verify git diff command using GitPython.

    Args:
        repo_path (str): Path to the Git repository.
    """
    try:
        repo = Repo(repo_path, search_parent_directories=True)
        if repo.bare:
            logger.error("Repository is bare.")
            print("Repository is bare.")
            return
        # Use only one flag: -M or --find-renames
        git_command = ['git', 'diff', '--cached', '--pretty=format:', '-M']
        logger.debug(f"Executing git command: {' '.join(git_command)}")
        diff_text = repo.git.diff('--cached', '--pretty=format:', '-M')  # Using -M
        print("Diff Output:")
        print(diff_text)
    except GitCommandError as e:
        logger.error("GitCommandError: %s", e)
        print(f"GitCommandError: {e}")
    except Exception as e:
        logger.error("Exception: %s", traceback.format_exc())
        print(f"Exception: {e}")


if __name__ == "__main__":
    main()

# Example of Desired Output:
# feat: Add LICENSE.txt file and CLI/GUI functionality for auto-generating Conventional Commit messages
