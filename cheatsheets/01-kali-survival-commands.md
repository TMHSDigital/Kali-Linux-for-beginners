# Kali Survival Commands: Quick Reference

Command reference for the Linux core (modules 01-02).

---

## Navigation & orientation

| Command | Action |
|---------|--------|
| `pwd` | Print working directory |
| `cd DIR` / `cd ..` / `cd` / `cd -` | Go to DIR / up one / home / previous |
| `ls -la` | Long listing incl. hidden files |
| `ls -lh` / `ls -lt` | Human sizes / sort by mtime |
| `tree -L 2` | Directory tree, 2 levels deep |
| `whoami` / `id` / `groups` | Current user / UID+GIDs / group names |
| `hostname` / `uname -a` | Machine name / full kernel info |

## Files & directories

| Command | Action |
|---------|--------|
| `touch FILE` | Create empty / update mtime |
| `mkdir -p a/b/c` | Create nested dirs |
| `cp SRC DST` / `cp -r DIR DST` / `cp -a` | Copy file / tree / tree preserving attrs |
| `mv SRC DST` | Move or rename |
| `rm FILE` / `rm -r DIR` / `rm -rf DIR` | Delete file / tree / force (DANGER) |
| `ln -s TARGET LINK` | Create symbolic link |
| `stat FILE` | Detailed metadata (perms octal+symbolic, times) |
| `file FILE` | Identify file type by content |

## Viewing & editing

| Command | Action |
|---------|--------|
| `cat FILE` / `cat -n` | Dump / with line numbers |
| `less FILE` | Page (q quit, / search) |
| `head -n N` / `tail -n N` | First / last N lines |
| `tail -f FILE` | Follow live (Ctrl-C to stop) |
| `nano FILE` / `vim FILE` | Edit |
| `wc -l` / `wc -c` | Count lines / bytes |

## Search

| Command | Action |
|---------|--------|
| `find / -name "NAME" 2>/dev/null` | Find by name, hide errors |
| `find DIR -type f -name "*.conf"` | Regular files matching glob |
| `find / -perm -u=s -type f 2>/dev/null` | SUID binaries (privesc audit) |
| `find DIR -mmin -10` | Modified in last 10 min |
| `grep "PAT" FILE` | Lines matching |
| `grep -i` / `-r` / `-n` / `-v` / `-c` | Ignore case / recurse / line no. / invert / count |
| `which CMD` / `whereis CMD` | Locate an executable |
| `locate NAME` | Fast filename search (needs `updatedb`) |

## Streams, pipes, redirection

| Syntax | Action |
|--------|--------|
| `cmd > file` | stdout → file (overwrite) |
| `cmd >> file` | stdout → file (append) |
| `cmd 2> file` | stderr → file |
| `cmd > file 2>&1` | stdout+stderr → file |
| `cmd &> file` | Same (bash shorthand) |
| `cmd 2>/dev/null` | Discard errors |
| `a \| b \| c` | Pipe stdout → next stdin |
| `cmd < file` | file → stdin |
| `tee file` | stdout → screen AND file |

## History & shortcuts

| Command / key | Action |
|---------------|--------|
| `history` / `history \| tail` | Command history |
| `!!` / `!N` / `!str` | Rerun last / #N / last starting "str" |
| `sudo !!` | Rerun previous with sudo |
| `Ctrl-R` | Reverse-search history |
| `Ctrl-C` / `Ctrl-D` / `Ctrl-Z` | Interrupt / EOF / suspend |
| `Ctrl-A` / `Ctrl-E` | Line start / end |
| `Ctrl-L` | Clear screen |

## Users, groups, privileges

| Command | Action |
|---------|--------|
| `sudo CMD` | Run one command as root |
| `sudo -i` / `su -` | Root shell (your pw / root's pw) |
| `sudo -l` | List your sudo rights |
| `sudo -u USER CMD` | Run as another user |
| `sudo visudo` | Safely edit sudoers |
| `useradd -m -s /bin/bash U` | Create user + home + shell |
| `passwd [U]` | Set password |
| `usermod -aG GROUP U` | **Append** user to group |
| `userdel -r U` | Delete user + home |
| `groupadd G` / `groupdel G` | Add / remove group |

## Permissions & ownership

| Command | Action |
|---------|--------|
| `chmod 644 F` / `755` / `600` / `700` | Octal modes |
| `chmod u+x,go-w F` | Symbolic modes |
| `chmod -R o-rwx DIR` | Recurse |
| `chown U:G F` / `chown -R` | Change owner:group |
| `chgrp G F` | Change group only |
| `umask` | Show/set default-permission mask |

## Processes & services

| Command | Action |
|---------|--------|
| `ps aux` / `ps -ef --forest` | All processes / tree |
| `top` / `htop` | Live process view |
| `pgrep -f "PAT"` / `pidof NAME` | Find PID(s) |
| `kill PID` / `kill -9 PID` | SIGTERM / SIGKILL |
| `pkill -f "PAT"` / `killall NAME` | Kill by pattern / name |
| `jobs` / `bg` / `fg` / `CMD &` | Job control |
| `nohup CMD &` | Survive logout |
| `systemctl status\|start\|stop\|restart\|enable\|disable NAME` | Manage service |
| `systemctl enable --now NAME` | Enable + start |
| `journalctl -u NAME -f` | Follow a unit's logs |

## Packages (Debian/Kali)

| Command | Action |
|---------|--------|
| `sudo apt update` | Refresh package index |
| `sudo apt upgrade` / `full-upgrade` | Upgrade packages |
| `sudo apt install PKG` | Install |
| `sudo apt remove PKG` / `purge` | Remove / + config |
| `apt search TERM` / `apt show PKG` | Find / details |
| `dpkg -l` / `dpkg -L PKG` | List installed / files of PKG |

## Networking basics

| Command | Action |
|---------|--------|
| `ip a` / `ip -brief a` | Interfaces & IPs |
| `ip route` | Routing table / default gw |
| `ss -tuln` / `ss -tulpn` | Listening sockets / + process |
| `dig +short NAME` / `dig -x IP` | DNS lookup / reverse |
| `ping -c 4 HOST` | Reachability test |
| `curl -I URL` | HTTP headers only (note: may be gated by ctx-mode) |

## Getting help

| Command | Action |
|---------|--------|
| `man CMD` | Manual page |
| `CMD --help` | Flag summary |
| `apropos TERM` / `whatis CMD` | Search man DB / one-liner |
| `type CMD` | builtin / alias / binary? |
