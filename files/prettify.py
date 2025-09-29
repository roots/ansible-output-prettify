"""
Ansible callback plugin for beautiful Laravel Artisan-style output
"""

import os
import time
import sys
from datetime import datetime
from ansible.plugins.callback import CallbackBase

# Simple ANSI color handling for all Ansible versions
COLORS = {
    'green': '\033[0;32m',
    'red': '\033[0;31m',
    'yellow': '\033[0;33m',
    'cyan': '\033[0;36m',
    'bright_red': '\033[1;31m',
    'blue': '\033[0;34m',
    'purple': '\033[1;35m',
    'gray': '\033[0;90m',
    'white': '\033[0;37m',
    'normal': '\033[0m'
}

def color_text(text, color):
    """Apply ANSI color to text"""
    return f"{COLORS.get(color, '')}{text}{COLORS['normal']}"


class CallbackModule(CallbackBase):
    """
    A callback plugin that makes ansible output beautiful like Laravel Artisan
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'prettify'

    # Constants
    MIN_TERMINAL_WIDTH = 60
    MAX_TASK_WIDTH_RATIO = 0.7  # Use 70% of terminal for task names
    TIMING_SPACE = 8            # "1234ms" + padding
    STATUS_SPACE = 8            # "SKIPPED" is longest
    LONGEST_STATUS = 7          # "SKIPPED" or "CHANGED"
    PREFIX_SPACE = 6            # "  ✓ " + " "
    MIN_DOTS = 3

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.start_time = time.time()
        self.task_start_time = None
        self.play_start_time = None
        self.last_task = None
        self.last_role = None
        self.cached_terminal_width = None

        # Detect Ansible version for compatibility
        self._detect_ansible_version()

        # Configuration options (can be set via environment variables)
        self.show_timestamps = os.environ.get('ANSIBLE_PRETTIFY_SHOW_TIMESTAMPS', 'false').lower() == 'true'
        self.show_timing = os.environ.get('ANSIBLE_PRETTIFY_SHOW_TIMING', 'true').lower() == 'true'

        # Colors and symbols
        self.colors = {
            'success': 'green',
            'failed': 'red',
            'changed': 'yellow',
            'skipped': 'cyan',
            'unreachable': 'bright_red',
            'info': 'blue',
            'header': 'purple',
            'task_name': 'normal',  # Default terminal color
            'dots': 'gray',
            'timing': 'gray',
        }

        self.symbols = {
            'success': '✓',
            'failed': '✗',
            'changed': '~',
            'skipped': '→',
            'unreachable': '⚠',
            'running': '●',
        }

    def _colorize(self, msg, color):
        """Apply color to message"""
        return color_text(msg, color)

    def _detect_ansible_version(self):
        """Detect Ansible version for compatibility adjustments"""
        try:
            import ansible
            self.ansible_version = ansible.__version__
            # Parse major.minor version
            version_parts = self.ansible_version.split('.')
            self.ansible_major = int(version_parts[0])
            self.ansible_minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        except:
            # Fallback for unknown versions
            self.ansible_version = "unknown"
            self.ansible_major = 2
            self.ansible_minor = 9

    def _get_terminal_width(self):
        """Get terminal width with caching and minimum width enforcement"""
        if self.cached_terminal_width is None:
            try:
                import shutil
                width = shutil.get_terminal_size().columns
                self.cached_terminal_width = max(width, self.MIN_TERMINAL_WIDTH)
            except:
                self.cached_terminal_width = 80  # Fallback
        return self.cached_terminal_width

    def _print_header(self, msg, color=None):
        """Print a header message"""
        if color is None:
            color = self.colors['header']

        # Clean single line header like Laravel Artisan
        self._display.display("")
        header_msg = f" {msg} "
        self._display.display(self._colorize(header_msg, color))
        self._display.display("")

    def _print_task_banner(self, task_name, host=None):
        """Print task banner like Laravel Artisan"""
        # Don't print individual task banners - let the results handle it
        pass

    def _get_task_role(self, task):
        """Extract role name from task using multiple fallback methods"""
        # List of attribute paths to try for role objects and their name methods
        role_paths = [
            ('_role', ['_role_name', 'get_name']),
            ('role', ['_role_name', 'get_name']),
        ]

        # Try direct role attribute access
        for attr, name_methods in role_paths:
            role_obj = getattr(task, attr, None)
            if role_obj:
                for name_method in name_methods:
                    if hasattr(role_obj, name_method):
                        role_name = getattr(role_obj, name_method)
                        if callable(role_name):
                            role_name = role_name()
                        if role_name:
                            return role_name

        # Try parent task for included/imported tasks
        parent = getattr(task, '_parent', None)
        if parent:
            parent_role = getattr(parent, '_role', None)
            if parent_role:
                role_name = getattr(parent_role, '_role_name', None)
                if role_name:
                    return role_name

        # Fallback: extract from file path
        if hasattr(task, 'get_path'):
            try:
                task_path = task.get_path()
                if task_path and '/roles/' in task_path:
                    # Extract role name from path like /path/to/roles/role-name/tasks/main.yml
                    return task_path.split('/roles/')[1].split('/')[0]
            except (AttributeError, IndexError):
                pass

        return ""

    def _print_result(self, result, status):
        """Print task result with timing"""
        symbol = self.symbols.get(status, self.symbols['success'])
        status_color = self.colors.get(status, self.colors['success'])

        # Build result line like Laravel Artisan
        task_name = result._task.name
        if not task_name or not task_name.strip():
            task_name = f"[{result._task.action}]"

        # Check if we need to show a role header
        current_role = self._get_task_role(result._task)
        if current_role and current_role != getattr(self, 'last_role', None):
            # Show role header
            self._display.display("")
            role_header = f"┌─ {current_role}"
            self._display.display(self._colorize(role_header, self.colors['info']))
            self.last_role = current_role

        display_name = task_name

        # Add timing if enabled
        timing_info = ""
        if self.show_timing and self.task_start_time:
            duration = time.time() - self.task_start_time
            timing_info = f"{duration * 1000:.0f}ms"

        status_text = {
            'changed': 'CHANGED',
            'failed': 'FAILED',
            'skipped': 'SKIPPED',
            'unreachable': 'UNREACHABLE'
        }.get(status, 'DONE')

        # Right-pad status text to make all statuses the same width
        status_text = status_text.ljust(self.LONGEST_STATUS)

        # Dynamic layout based on terminal width
        # Layout: "  ✓ Task name ................................. 123ms DONE"

        # Get terminal width with caching and minimum width enforcement
        max_width = self._get_terminal_width()

        # Reserve space for timing and status at the end
        reserved_space = self.TIMING_SPACE + self.STATUS_SPACE

        # Maximum space for task name and dots
        max_task_width = max_width - self.PREFIX_SPACE - reserved_space

        if len(display_name) > max_task_width:
            # Need to wrap - find good break point
            # Prefer spaces, avoid breaking paths poorly
            break_chars = [' ', '_', '-', ':']  # Removed '.' and '/' to avoid bad path breaks
            best_break = -1

            # Look for break point - search from ideal length backwards
            search_start = min(max_task_width - 3, len(display_name) - 1)
            search_end = max(25, max_task_width // 2)  # Increased minimum to avoid very short first lines

            for i in range(search_start, search_end, -1):
                if i < len(display_name) and display_name[i] in break_chars:
                    # Don't break right after a short word (less than 3 chars)
                    if i > 3 and display_name[i-3:i].strip():
                        best_break = i
                        break

            if best_break > 0:
                # Split at word boundary
                first_part = display_name[:best_break].rstrip()
                second_part = display_name[best_break:].lstrip()

                # First line - no dots, no timing, no status - just task name
                first_line = f"  {color_text(symbol, status_color)} {color_text(first_part, self.colors['task_name'])}"
                self._display.display(first_line)

                # Second line with timing and status - right aligned
                second_prefix = "    "  # 4 spaces for continuation
                second_line_prefix = f"{second_prefix}{color_text(second_part, self.colors['task_name'])} "

                # Calculate suffix for second line
                suffix_parts = []
                if timing_info:
                    suffix_parts.append(color_text(timing_info, self.colors['timing']))
                suffix_parts.append(" " + color_text(status_text, status_color))
                suffix = "".join(suffix_parts)

                # Calculate dots for second line
                prefix_len = len(f"{second_prefix}{second_part} ")  # Without color codes
                suffix_len = len(f"{timing_info} {status_text}")  # Without color codes
                dots_needed = max_width - prefix_len - suffix_len
                dots = "." * max(dots_needed, self.MIN_DOTS)

                # Build second line
                second_line = f"{second_line_prefix}{color_text(dots, self.colors['dots'])}{suffix}"
                self._display.display(second_line)
                return
            else:
                # No good break point - truncate
                display_name = display_name[:max_task_width-3] + "..."

        # Normal single line case - build from scratch with right alignment
        prefix = f"  {color_text(symbol, status_color)} {color_text(display_name, self.colors['task_name'])} "

        # Calculate how much space we need for the suffix
        suffix_parts = []
        if timing_info:
            suffix_parts.append(color_text(timing_info, self.colors['timing']))
        suffix_parts.append(" " + color_text(status_text, status_color))
        suffix = "".join(suffix_parts)

        # Calculate dots needed to fill the space
        prefix_len = len(f"  {symbol} {display_name} ")  # Without color codes
        suffix_len = len(f"{timing_info} {status_text}")  # Without color codes
        dots_needed = max_width - prefix_len - suffix_len
        dots = "." * max(dots_needed, self.MIN_DOTS)

        # Build the complete line
        line = f"{prefix}{color_text(dots, self.colors['dots'])}{suffix}"
        self._display.display(line)

        # Show failure details
        if status == 'failed' and 'msg' in result._result:
            error_msg = f"    Error: {result._result['msg']}"
            self._display.display(self._colorize(error_msg, self.colors['failed']))

    def v2_playbook_on_start(self, playbook):
        """Called when the playbook starts"""
        self.start_time = time.time()
        # Don't print "Starting Ansible Playbook" - too verbose

    def v2_playbook_on_play_start(self, play):
        """Called when a play starts"""
        self.play_start_time = time.time()
        # Reset terminal width cache for new play (terminal may have been resized)
        self.cached_terminal_width = None
        play_name = play.get_name().strip()
        if not play_name:
            play_name = "Unnamed Play"

        # Clean play header like Laravel Artisan
        self._display.display("")
        play_msg = f"PLAY [{play_name}]"
        self._display.display(self._colorize(play_msg, self.colors['info']))
        self._display.display("")

    def v2_playbook_on_task_start(self, task, is_conditional):
        """Called when a task starts"""
        self.task_start_time = time.time()
        self.last_task = task
        # Don't print task start banners - cleaner output

    def v2_runner_on_ok(self, result):
        """Called when a task succeeds"""
        if result._result.get('changed', False):
            self._print_result(result, 'changed')
        else:
            self._print_result(result, 'success')

    def v2_runner_on_failed(self, result, ignore_errors=False):
        """Called when a task fails"""
        self._print_result(result, 'failed')

    def v2_runner_on_skipped(self, result):
        """Called when a task is skipped"""
        self._print_result(result, 'skipped')

    def v2_runner_on_unreachable(self, result):
        """Called when a host is unreachable"""
        self._print_result(result, 'unreachable')

    def v2_playbook_on_stats(self, stats):
        """Called when the playbook finishes"""
        total_time = time.time() - self.start_time

        self._display.display("")

        # Show host stats in clean format like Laravel Artisan
        hosts = sorted(stats.processed.keys())

        # Create a clean summary table
        for host in hosts:
            summary = stats.summarize(host)

            # Build status parts with symbols and consistent spacing
            status_parts = []
            if summary['ok'] > 0:
                status_parts.append(self._colorize(f"✓ {summary['ok']} successful", self.colors['success']))
            if summary['changed'] > 0:
                status_parts.append(self._colorize(f"~ {summary['changed']} changed", self.colors['changed']))
            if summary['failures'] > 0:
                status_parts.append(self._colorize(f"✗ {summary['failures']} failed", self.colors['failed']))
            if summary['unreachable'] > 0:
                status_parts.append(self._colorize(f"⚠ {summary['unreachable']} unreachable", self.colors['unreachable']))
            if summary['skipped'] > 0:
                status_parts.append(self._colorize(f"→ {summary['skipped']} skipped", self.colors['skipped']))

            # Format the host summary nicely
            host_header = self._colorize(f"  {host}", self.colors['info'])
            self._display.display(host_header)
            for status_part in status_parts:
                self._display.display(f"    {status_part}")

        # Determine if this is a deployment or provision based on playbook name
        playbook_name = ""
        try:
            # Try to get the playbook name from the environment or context
            import sys
            if len(sys.argv) > 0:
                for arg in sys.argv:
                    if arg.endswith('.yml') or arg.endswith('.yaml'):
                        playbook_name = arg.lower()
                        break
        except:
            pass

        # Show context-aware completion message
        self._display.display("")
        if 'deploy' in playbook_name:
            completion_msg = f"🚀 Deployment completed successfully in {total_time:.1f}s"
        elif 'provision' in playbook_name:
            completion_msg = f"⚙️ Provisioning completed successfully in {total_time:.1f}s"
        else:
            completion_msg = f"✅ Playbook completed successfully in {total_time:.1f}s"

        self._display.display(self._colorize(completion_msg, self.colors['success']))
        self._display.display("")

