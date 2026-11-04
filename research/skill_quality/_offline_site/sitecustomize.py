"""Test-process egress guard, not an OS sandbox. Loopback remains available."""

import ipaddress
import socket

_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex
_getaddrinfo = socket.getaddrinfo


def _local(host):
    if host in (None, "", "localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


def _checked_connect(self, address):
    if isinstance(address, tuple) and not _local(address[0]):
        raise OSError("Research offline test guard blocks external egress")
    return _connect(self, address)


def _checked_connect_ex(self, address):
    if isinstance(address, tuple) and not _local(address[0]):
        raise OSError("Research offline test guard blocks external egress")
    return _connect_ex(self, address)


def _checked_getaddrinfo(host, *args, **kwargs):
    if not _local(host):
        raise OSError("Research offline test guard blocks external DNS")
    return _getaddrinfo(host, *args, **kwargs)


socket.socket.connect = _checked_connect
socket.socket.connect_ex = _checked_connect_ex
socket.getaddrinfo = _checked_getaddrinfo
