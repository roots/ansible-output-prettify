# Ansible Output Prettify

Transform your Ansible playbook output into beautiful console output

## Features

- Beautiful colorized output
- Compact, readable format
- Role grouping to organize tasks by role

| Before (Default Ansible) | After (Prettified) |
|:-------------------------:|:------------------:|
| ![Before](https://roots.io/app/uploads/ansible-output-default.png) | ![After](https://roots.io/app/uploads/ansible-output-prettify.png) |

## Quick Start

```yaml
# requirements.yml
- src: https://github.com/roots/ansible-output-prettify.git
  name: ansible-output-prettify
```

```bash
ansible-galaxy install -r requirements.yml
```

```yaml
# your-playbook.yml
- hosts: localhost
  roles:
    - ansible-output-prettify

- hosts: your_servers
  roles:
    - your_other_roles
```

## Configuration

### Role variables

Set these in your playbook or inventory:

```yaml
# Control automatic ansible.cfg configuration
prettify_auto_configure: true  # default: true

# Callback plugin settings (via environment variables)
ANSIBLE_PRETTIFY_SHOW_TIMING: true      # default: true
ANSIBLE_PRETTIFY_SHOW_TIMESTAMPS: false # default: false
```

### Environment Variables

- `ANSIBLE_PRETTIFY_SHOW_TIMING=true` - Show task execution times
- `ANSIBLE_PRETTIFY_SHOW_TIMESTAMPS=false` - Show timestamps for each task

### Ansible configuration options

Add to your `ansible.cfg` for the best experience:

```ini
[defaults]
stdout_callback = prettify
callback_plugins = ~/.ansible/plugins/callback
```
