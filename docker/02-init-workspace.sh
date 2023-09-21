#!/bin/bash
set -e

apt-get update
apt-get install curl -y

curl ident.me

curl --location 'http://api:8000/api/v1/namespace/' \
--header 'Content-Type: application/json' \
--data '{
    "slug": "leap_space",
    "name": "Leap Space"
}'