# ftp-service: vsftpd on Alpine with anonymous AND local logins enabled.
# Everything (USER/PASS, commands, listings, file contents) crosses the wire in
# cleartext, which is the point of the lab. Multi-arch: runs on amd64 and arm64.
FROM alpine:3.24@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6

RUN apk add --no-cache vsftpd

COPY vsftpd.conf /etc/vsftpd/vsftpd.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Anonymous root must exist and must NOT be writable by the ftp user, or
# vsftpd refuses to start. Seed a file so ftp-data has something to carry.
RUN chmod 755 /usr/local/bin/entrypoint.sh \
 && mkdir -p /srv/ftp/pub \
 && printf 'Welcome to the ACME public FTP drop (lab).\nAnonymous access is enabled on purpose.\n' \
      > /srv/ftp/pub/welcome.txt \
 && chown -R root:root /srv/ftp && chmod -R 755 /srv/ftp

EXPOSE 21 21100-21110
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD nc -z 127.0.0.1 21 || exit 1
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
