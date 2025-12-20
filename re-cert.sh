#!/usr/bin/bash

# Renews SSL certification

docker stop sabc-nginx
certbot renew --force-renewal
cp /etc/letsencrypt/live/saustinbc.com/fullchain.pem /home/sabc/SABC/ssl/
cp /etc/letsencrypt/live/saustinbc.com/privkey.pem /home/sabc/SABC/ssl/
docker start sabc-nginx