#!/bin/sh
# Create the named local FTP user from the environment, then run vsftpd in the
# foreground. Idempotent, so container restarts are safe.
set -eu

FTP_USER="${FTP_USER:-labuser}"
FTP_PASS="${FTP_PASS:-labpass}"

if ! id "$FTP_USER" >/dev/null 2>&1; then
  adduser -D -h "/home/$FTP_USER" -s /bin/sh "$FTP_USER"
  printf 'Internal notes (lab). Nothing here should be on a cleartext FTP server.\n' \
    > "/home/$FTP_USER/notes.txt"
  chown "$FTP_USER:$FTP_USER" "/home/$FTP_USER/notes.txt"
fi
echo "$FTP_USER:$FTP_PASS" | chpasswd >/dev/null 2>&1

exec /usr/sbin/vsftpd /etc/vsftpd/vsftpd.conf
