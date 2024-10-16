# Git Commit Message Generator

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)

A Python tool that automatically generates Git commit messages following the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification. Leveraging Groq's AI API, this tool ensures your commit history is clean, meaningful, and adheres to best practices. It offers both Command-Line Interface (CLI) and Graphical User Interface (GUI) options to cater to different user preferences.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [CLI](#cli)
  - [GUI](#gui)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)

## Features

- **AI-Powered Commit Messages**: Utilizes Groq's AI to generate meaningful commit messages based on staged changes.
- **Conventional Commits Compliance**: Ensures commit messages follow the Conventional Commits specification for consistency and clarity.
- **Dual Interface**: Offers both CLI and GUI options for flexible usage.
- **Environment Variable Management**: Uses a `.env` file to securely manage API keys.
- **Git Integration**: Automatically interacts with your Git repository to fetch changes and create commits.

## Prerequisites

Before installing and using the Git Commit Message Generator, ensure you have the following:

- **Python 3.7 or higher**: [Download Python](https://www.python.org/downloads/)
- **Git**: [Download Git](https://git-scm.com/downloads)

## Installation

1. **Clone the Repository**

```bash
git clone https://github.com/0vg/goodgit.git
cd goodgit
```

2. **Create a Virtual Environment (Optional but Recommended)**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**

```bash
pip install -r requirements.txt
```

## Configuration

1. **Obtain a Groq API Key**

- Create an API Key: Visit Groq's API Key Creation Page to generate your API key.

2. **Set Up Environment Variables**

   To securely manage your Groq API key, use a `.env` file.

   1. **Create a .env File**

      In the root directory of the project, create a file named .env.

      ```env
      GROQ_API_KEY=your_actual_groq_api_key_here
      ```

## Usage

The tool offers both CLI and GUI options.

### CLI

1. **Generate Commit Message**

   To generate a commit message based on staged changes:

   ```bash
   python goodgit.py --cli
   ```

   This command will print the generated commit message to the console.

2. **Generate and Commit**

   To generate a commit message and create a commit in one step:

   ```bash
   python goodgit.py --cli --commit
   ```

   This command will generate the commit message and create a commit in your Git repository with the generated message.

### GUI

1. **Launch the GUI**

   ```bash
   python commit_tool.py --gui
   ```

   This command will open the graphical interface.

2. **Using the GUI**

   - Generate Commit Message: Click the "Generate Commit Message" button to fetch and display the commit message based on staged changes.
   - Review/Edit: You can review or manually edit the commit message in the text area.
   - Commit: Click the "Commit" button to create the commit with the displayed message.

## Examples

### Example 1: Generating a Commit Message via CLI

```bash
$ git add .
$ python goodgit.py --cli

Generated Commit Message:
feat(parser): add ability to parse nested JSON structures
```

### Example 2: Generating and Committing via CLI

```bash
$ git add .
$ python goodgit.py --cli --commit

Generated Commit Message:
fix(auth): resolve issue with token expiration

Commit created successfully.
```

### Example 3: Using the GUI

1. Launch the GUI:

```bash
python goodgit.py --gui
```

2. Click "Generate Commit Message". The generated message appears in the text area.
3. Review or edit the message as needed.
4. Click "Commit" to create the commit.

## Contributing

Contributions are welcome! Please follow these steps to contribute:

1. **Fork the Repository**
   Click the "Fork" button at the top-right corner of this page.

2. **Clone your fork**

   ```bash
   git clone https://github.com/yourusername/goodgit.git
   cd goodgit
   ```

3. **Create a new branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make your changes**
   Implement your feature or bug fix.

5. **Commit your changes**

   ```bash
   git commit -m "feat: add your feature description"
   ```

6. **Push your fork**

   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a pull request**
   Navigate to the original repository and click "Compare & pull request".

## License

This project is licensed under the MIT License. See LICENSE.txt for details.
