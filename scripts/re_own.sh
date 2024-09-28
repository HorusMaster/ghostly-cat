#!/usr/bin/env bash
# Using the dev containers frequently messes up the ownership of
# chmod +x re_own.sh
# source files so this fixes it
sudo chown -R $USER:$USER ~/ghostly-cat