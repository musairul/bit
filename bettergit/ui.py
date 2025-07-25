"""User interface utilities for interactive prompts and displays."""

import inquirer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from typing import List, Dict, Any, Optional, Union
import logging
import sys
import os
import emoji


logger = logging.getLogger(__name__)

# Test if we can use emojis or need ASCII fallback
def _test_unicode_support():
    """Test if the current terminal supports emoji output."""
    try:
        # Try to encode some test emojis with the system encoding
        test_emoji = "✅🌿📋"
        test_emoji.encode(sys.stdout.encoding or 'utf-8')
        return True
    except (UnicodeEncodeError, LookupError):
        return False

# Determine symbol set based on terminal capabilities
_CAN_USE_EMOJI = _test_unicode_support()

if _CAN_USE_EMOJI:
    # Use beautiful emojis for better visual experience
    SYMBOLS = {
        'success': '✅',
        'error': '❌', 
        'warning': '⚠️',
        'info': 'ℹ️',
        'branch': '🌿',
        'file': '📄',
        'untracked': '❓',
        'staged': '➕',
        'modified': '📝',
        'clipboard': '📋',
        'save': '💾',
        'remote': '🌐',
        'user': '👤',
        'stash': '📦',
        'graph': '📊',
        'key': '🔑',
        'lock': '🔒',
    }
else:
    # Fallback to ASCII symbols for compatibility
    SYMBOLS = {
        'success': 'v',
        'error': 'X', 
        'warning': '!',
        'info': 'i',
        'branch': '*',
        'file': '+',
        'untracked': '?',
        'staged': '+',
        'modified': 'M',
        'clipboard': '#',
        'save': 'S',
        'remote': '@',
        'user': 'U',
        'stash': 'B',
        'graph': 'G',
        'key': 'K',
        'lock': 'L',
    }

# Configure console appropriately
if _CAN_USE_EMOJI:
    console = Console(
        force_terminal=True,
        width=None,
        emoji=True
    )
else:
    console = Console(
        force_terminal=True,
        width=None,
        legacy_windows=True
    )


class UIError(Exception):
    """Raised when there's an error with UI operations."""
    pass


def _safe_print(content, **kwargs):
    """Safely print content to the console."""
    try:
        console.print(content, **kwargs)
    except Exception as e:
        # Last resort: print as plain text
        logger.error(f"Console print failed: {e}")
        print(str(content))


def print_success(message: str):
    """Print a success message in green."""
    _safe_print(f"{SYMBOLS['success']} {message}", style="bold green")


def print_error(message: str):
    """Print an error message in red."""
    _safe_print(f"{SYMBOLS['error']} {message}", style="bold red")


def print_warning(message: str):
    """Print a warning message in yellow."""
    _safe_print(f"{SYMBOLS['warning']} {message}", style="bold yellow")


def print_info(message: str):
    """Print an info message in blue."""
    _safe_print(f"{SYMBOLS['info']}  {message}", style="bold blue")


def confirm(message: str, default: bool = False) -> bool:
    """Show a yes/no confirmation prompt."""
    try:
        questions = [
            inquirer.Confirm('confirm', message=message, default=default)
        ]
        answers = inquirer.prompt(questions)
        return answers['confirm'] if answers else default
    except KeyboardInterrupt:
        return False
    except Exception as e:
        logger.error(f"Confirmation prompt failed: {e}")
        return default


def prompt_text(message: str, default: str = "") -> str:
    """Show a text input prompt."""
    try:
        questions = [
            inquirer.Text('input', message=message, default=default)
        ]
        answers = inquirer.prompt(questions)
        return answers['input'] if answers else default
    except KeyboardInterrupt:
        return default
    except Exception as e:
        logger.error(f"Text prompt failed: {e}")
        return default


def prompt_password(message: str) -> str:
    """Show a password input prompt (hidden input)."""
    try:
        questions = [
            inquirer.Password('password', message=message)
        ]
        answers = inquirer.prompt(questions)
        return answers['password'] if answers else ""
    except KeyboardInterrupt:
        return ""
    except Exception as e:
        logger.error(f"Password prompt failed: {e}")
        return ""


def select_from_list(message: str, choices: List[Union[str, tuple]], 
                    default: Optional[str] = None) -> Optional[str]:
    """Show a selection list."""
    try:
        if not choices:
            print_warning("No options available to select from.")
            return None
            
        questions = [
            inquirer.List('choice', message=message, choices=choices, default=default)
        ]
        answers = inquirer.prompt(questions)
        return answers['choice'] if answers else None
    except KeyboardInterrupt:
        return None
    except Exception as e:
        logger.error(f"List selection failed: {e}")
        return None


def select_undo_point(message: str, choices: List[str]) -> Optional[int]:
    """Show a custom undo point selection with progressive highlighting.
    
    Returns the index of the selected choice, or None if cancelled.
    """
    try:
        import msvcrt
        import os
        
        if not choices:
            print_warning("No options available to select from.")
            return None
        
        current_pos = 0
        menu_lines_printed = 0
        header_displayed = False
        
        def clear_menu_lines(num_lines):
            """Clear only the menu lines, not the header."""
            if num_lines > 0:
                # Move cursor up and clear each line
                for _ in range(num_lines):
                    print('\033[1A\033[2K', end='')  # Move up one line and clear it
        
        def display_header():
            """Display the static header only once."""
            print(f"\n{message}")
            print("Use arrow keys to navigate, Enter to select, Esc or Ctrl+C to cancel")
            print()  # Empty line for spacing
        
        def display_menu():
            nonlocal menu_lines_printed
            
            # Clear previous menu output (but not header)
            clear_menu_lines(menu_lines_printed)
            
            # Calculate visible window for large lists
            max_visible = 10  # Show max 10 items at once
            start_idx = max(0, current_pos - max_visible // 2)
            end_idx = min(len(choices), start_idx + max_visible)
            
            # Adjust start if we're near the end
            if end_idx - start_idx < max_visible and start_idx > 0:
                start_idx = max(0, end_idx - max_visible)
            
            lines_count = 0  # No dynamic counter line
            
            # Show ellipsis if there are items above
            if start_idx > 0:
                print("  ...")
                lines_count += 1
            
            # Display visible choices
            for i in range(start_idx, end_idx):
                choice = choices[i]
                if i <= current_pos:
                    # Highlight selected items in blue with > prefix
                    if i == current_pos:
                        print(f"\033[94m\033[7m> {choice}\033[0m")  # Reverse video for current selection
                    else:
                        print(f"\033[94m> {choice}\033[0m")
                else:
                    # Normal display for unselected items
                    print(f"  {choice}")
                lines_count += 1
            
            # Show ellipsis if there are items below
            if end_idx < len(choices):
                print("  ...")
                lines_count += 1
            
            menu_lines_printed = lines_count
        
        # Display header once
        display_header()
        header_displayed = True
        
        # Initial menu display
        display_menu()
        
        while True:
            # Get key input
            if os.name == 'nt':  # Windows
                key = msvcrt.getch()
                if key == b'\xe0':  # Arrow key prefix on Windows
                    key = msvcrt.getch()
                    if key == b'H':  # Up arrow
                        if current_pos > 0:
                            current_pos -= 1
                            display_menu()
                    elif key == b'P':  # Down arrow
                        if current_pos < len(choices) - 1:
                            current_pos += 1
                            display_menu()
                elif key == b'\r':  # Enter key
                    return current_pos
                elif key == b'\x1b':  # Escape key
                    return None
                elif key == b'\x03':  # Ctrl+C
                    return None
            else:  # Unix/Linux/macOS
                import sys, tty, termios
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setraw(sys.stdin.fileno())
                    key = sys.stdin.read(1)
                    if key == '\x1b':  # Escape sequence
                        key2 = sys.stdin.read(1)
                        if key2 == '[':
                            key3 = sys.stdin.read(1)
                            if key3 == 'A':  # Up arrow
                                if current_pos > 0:
                                    current_pos -= 1
                                    display_menu()
                            elif key3 == 'B':  # Down arrow
                                if current_pos < len(choices) - 1:
                                    current_pos += 1
                                    display_menu()
                        elif key2 == '':  # Just escape
                            return None
                    elif key == '\r' or key == '\n':  # Enter
                        return current_pos
                    elif key == '\x03':  # Ctrl+C
                        return None
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    
    except KeyboardInterrupt:
        return None
    except Exception as e:
        logger.error(f"Undo selection failed: {e}")
        # Fallback to regular selection
        result = select_from_list(message, choices)
        if result:
            return choices.index(result)
        return None


def select_multiple(message: str, choices: List[Union[str, tuple]]) -> List[str]:
    """Show a multiple selection checkbox list."""
    try:
        if not choices:
            print_warning("No options available to select from.")
            return []
            
        questions = [
            inquirer.Checkbox('choices', message=message, choices=choices)
        ]
        answers = inquirer.prompt(questions)
        return answers['choices'] if answers else []
    except KeyboardInterrupt:
        return []
    except Exception as e:
        logger.error(f"Multiple selection failed: {e}")
        return []


def display_table(title: str, headers: List[str], rows: List[List[str]], 
                  show_lines: bool = True):
    """Display a formatted table."""
    try:
        table = Table(title=title, show_lines=show_lines)
        
        for header in headers:
            table.add_column(header, style="cyan", no_wrap=True)
        
        for row in rows:
            table.add_row(*row)
        
        _safe_print(table)
    except Exception as e:
        logger.error(f"Table display failed: {e}")
        print_error(f"Failed to display table: {e}")


def display_list(title: str, items: List[str], numbered: bool = True):
    """Display a formatted list."""
    try:
        if numbered:
            _safe_print(f"\n[bold cyan]{title}[/bold cyan]")
            for i, item in enumerate(items, 1):
                _safe_print(f"  {i}. {item}")
        else:
            _safe_print(f"\n[bold cyan]{title}[/bold cyan]")
            for item in items:
                _safe_print(f"  • {item}")
        _safe_print("")
    except Exception as e:
        logger.error(f"List display failed: {e}")
        print_error(f"Failed to display list: {e}")


def display_panel(content: str, title: str = "", style: str = ""):
    """Display content in a bordered panel."""
    try:
        panel = Panel(content, title=title, border_style=style)
        _safe_print(panel)
    except Exception as e:
        logger.error(f"Panel display failed: {e}")
        print_error(f"Failed to display panel: {e}")


def display_git_graph(commits: List[Dict[str, Any]]):
    """Display a git commit graph using rich tree structure."""
    try:
        tree = Tree(f"{SYMBOLS['clipboard']} Commit History")
        
        for commit in commits:
            commit_hash = commit.get('hash', 'unknown')[:8]
            author = commit.get('author', 'unknown')
            message = commit.get('message', 'no message')
            date = commit.get('date', 'unknown')
            
            commit_text = f"[yellow]{commit_hash}[/yellow] [green]{author}[/green] [dim]{date}[/dim]"
            branch = tree.add(commit_text)
            branch.add(f"{SYMBOLS['file']} {message}")
        
        _safe_print(tree)
    except Exception as e:
        logger.error(f"Git graph display failed: {e}")
        print_error(f"Failed to display git graph: {e}")


def display_status_summary(status: Dict[str, Any]):
    """Display a comprehensive git status summary similar to git status."""
    try:
        content = []
        
        # Repository state (merge, rebase, etc.)
        if status.get('repo_state'):
            state = status['repo_state']
            if state == "MERGING":
                content.append(f"[bold red]{SYMBOLS['warning']} You are in the middle of a merge[/bold red]")
                content.append("  (fix conflicts and run [yellow]'bit save'[/yellow] to conclude merge)")
            elif state == "REBASING":
                content.append(f"[bold yellow]{SYMBOLS['warning']} You are in the middle of a rebase[/bold yellow]")
                content.append("  (fix conflicts and run [yellow]'git rebase --continue'[/yellow])")
            elif state == "CHERRY-PICKING":
                content.append(f"[bold yellow]{SYMBOLS['warning']} You are in the middle of a cherry-pick[/bold yellow]")
                content.append("  (fix conflicts and run [yellow]'git cherry-pick --continue'[/yellow])")
            elif state == "REVERTING":
                content.append(f"[bold yellow]{SYMBOLS['warning']} You are in the middle of a revert[/bold yellow]")
                content.append("  (fix conflicts and run [yellow]'git revert --continue'[/yellow])")
            elif state == "BISECTING":
                content.append(f"[bold cyan]{SYMBOLS['info']} You are in the middle of a bisect[/bold cyan]")
                content.append("  (run [yellow]'git bisect good/bad'[/yellow] to continue)")
            content.append("")
        
        # Branch information
        if status.get('branch'):
            branch_line = f"{SYMBOLS['branch']} On branch [bold cyan]{status['branch']}[/bold cyan]"
            
            # Add remote tracking info
            if status.get('remote_branch'):
                remote = status['remote_branch']
                branch_line += f" tracking [cyan]{remote}[/cyan]"
                
                # Add ahead/behind information
                ahead = status.get('ahead', 0)
                behind = status.get('behind', 0)
                
                if ahead > 0 and behind > 0:
                    content.append(branch_line)
                    content.append(f"  Your branch and '{remote}' have diverged,")
                    content.append(f"  and have {ahead} and {behind} different commits each, respectively.")
                    content.append("  (use [yellow]'bit pull'[/yellow] to merge the remote branch into yours)")
                elif ahead > 0:
                    content.append(branch_line)
                    content.append(f"  Your branch is ahead of '{remote}' by {ahead} commit{'s' if ahead != 1 else ''}.")
                    content.append("  (use [yellow]'bit push'[/yellow] to publish your local commits)")
                elif behind > 0:
                    content.append(branch_line)
                    content.append(f"  Your branch is behind '{remote}' by {behind} commit{'s' if behind != 1 else ''}.")
                    content.append("  (use [yellow]'bit pull'[/yellow] to update your local branch)")
                else:
                    content.append(branch_line)
                    content.append(f"  Your branch is up to date with '{remote}'.")
            else:
                content.append(branch_line)
                # Check if this branch has no upstream
                try:
                    from .core.git import run_git_command
                    run_git_command(['rev-parse', '--abbrev-ref', '@{upstream}'])
                except:
                    content.append("  No commits yet.")
            
            content.append("")
        
        # Merge conflicts
        if status.get('merge_conflicts'):
            conflicts = status['merge_conflicts']
            content.append(f"[bold red]{SYMBOLS['error']} You have unmerged paths.[/bold red]")
            content.append("  (fix conflicts and run [yellow]'bit save'[/yellow] to conclude merge)")
            content.append("  (use [yellow]'bit save --abort'[/yellow] to abort the merge)")
            content.append("")
            content.append(f"[bold red]Unmerged paths:[/bold red]")
            content.append("  (use [yellow]'git add <file>...'[/yellow] to mark resolution)")
            for file in conflicts[:10]:  # Limit display to first 10
                content.append(f"    [red]both modified:   {file}[/red]")
            if len(conflicts) > 10:
                content.append(f"    ... and {len(conflicts) - 10} more files")
            content.append("")
        
        # Changes to be committed (staged)
        staged_files = []
        if status.get('staged'):
            for item in status['staged']:
                if isinstance(item, tuple):
                    staged_files.append(item)
                else:
                    staged_files.append((item, 'modified'))
        if status.get('renamed'):
            staged_files.extend([(f, 'renamed') for f in status['renamed']])
        if status.get('copied'):
            staged_files.extend([(f, 'copied') for f in status['copied']])
        
        if staged_files:
            content.append(f"[bold green]Changes to be committed:[/bold green]")
            content.append("  (use [yellow]'bit undo'[/yellow] to unstage)")
            for file, change_type in staged_files[:15]:  # Limit display
                if change_type == 'renamed':
                    content.append(f"    [green]renamed:    {file}[/green]")
                elif change_type == 'copied':
                    content.append(f"    [green]copied:     {file}[/green]")
                elif change_type == 'deleted':
                    content.append(f"    [green]deleted:    {file}[/green]")
                elif change_type == 'new file':
                    content.append(f"    [green]new file:   {file}[/green]")
                else:
                    content.append(f"    [green]modified:   {file}[/green]")
            if len(staged_files) > 15:
                content.append(f"    ... and {len(staged_files) - 15} more files")
            content.append("")
        
        # Changes not staged for commit (modified)
        if status.get('modified'):
            modified = status['modified']
            content.append(f"[bold red]Changes not staged for commit:[/bold red]")
            content.append("  (use [yellow]'bit save'[/yellow] to stage and commit)")
            content.append("  (use [yellow]'git checkout -- <file>...'[/yellow] to discard changes)")
            for file in modified[:15]:  # Limit display
                content.append(f"    [red]modified:   {file}[/red]")
            if len(modified) > 15:
                content.append(f"    ... and {len(modified) - 15} more files")
            content.append("")
        
        # Untracked files
        if status.get('untracked'):
            untracked = status['untracked']
            content.append(f"[bold red]Untracked files:[/bold red]")
            content.append("  (use [yellow]'bit save'[/yellow] to include in what will be committed)")
            for file in untracked[:15]:  # Limit display
                content.append(f"    [red]{file}[/red]")
            if len(untracked) > 15:
                content.append(f"    ... and {len(untracked) - 15} more files")
            content.append("")
        
        # Stash information
        if status.get('stash_count', 0) > 0:
            stash_count = status['stash_count']
            content.append(f"{SYMBOLS['stash']} You have {stash_count} stash{'es' if stash_count != 1 else ''}")
            content.append("  (use [yellow]'bit list stashes'[/yellow]s to see them)")
            content.append("")
        
        # Clean working directory message
        if not any([
            status.get('staged'), status.get('modified'), status.get('untracked'),
            status.get('merge_conflicts'), status.get('renamed'), status.get('copied')
        ]):
            if status.get('ahead', 0) == 0 and status.get('behind', 0) == 0:
                content.append(f"[bold green]{SYMBOLS['success']} Nothing to commit, working tree clean[/bold green]")
            else:
                content.append(f"[bold green]{SYMBOLS['success']} Working tree clean[/bold green]")
        
        # Display the content
        if content:
            console.print("\n".join(content))
        
    except Exception as e:
        logger.error(f"Status display failed: {e}")
        print_error(f"Failed to display status: {e}")


def show_diff_preview(files: List[str], limit: int = 10):
    """Show a preview of files that would be affected."""
    try:
        if not files:
            print_info("No files would be affected.")
            return
        
        display_files = files[:limit]
        if len(files) > limit:
            display_files.append(f"... and {len(files) - limit} more files")
        
        display_list("Files that would be affected:", display_files, numbered=False)
        
    except Exception as e:
        logger.error(f"Diff preview failed: {e}")
        print_error(f"Failed to show diff preview: {e}")


def require_confirmation(action: str, target: str = "", 
                        danger_level: str = "medium") -> bool:
    """
    Require user confirmation for potentially dangerous actions.
    
    Args:
        action: The action being performed
        target: The target of the action (branch name, etc.)
        danger_level: "low", "medium", "high", or "extreme"
    """
    try:
        if danger_level == "extreme":
            # For extreme danger (like force push), require typing the target
            if target:
                typed_target = prompt_text(
                    f"This is a dangerous operation. Type '{target}' to confirm:"
                )
                return typed_target == target
            else:
                return confirm(f"This is a dangerous operation. Are you sure?", default=False)
        
        elif danger_level == "high":
            return confirm(f"Are you sure you want to {action}? This cannot be easily undone.", 
                          default=False)
        
        elif danger_level == "medium":
            return confirm(f"Are you sure you want to {action}?", default=True)
        
        else:  # low
            return True
            
    except Exception as e:
        logger.error(f"Confirmation failed: {e}")
        return False
