#!/usr/bin/bash
pacman -Syu --noconfirm

pacman -S --noconfirm python2 python2-setuptools python2-pip nginx base-devel libxml2 libxslt
pip2 install feedparser lxml ntplib passlib pyOpenSSL pyparsing python-iptables python-nginx uWSGI wsgiref Mock
pip2 install gevent greenlet
