# proxy_utils.py

import functools
import ipaddress
from urllib.parse import urlparse
from toolbox import get_conf
import requests

PROXY_BYPASS_PATTERNS = get_conf('PROXY_BYPASS_PATTERNS')

def is_private_ip(ip_address):
    """
    检查给定的IP地址是否为私有IP。
    支持IPv4和IPv6。
    """
    try:
        ip = ipaddress.ip_address(ip_address)
        if ip.version == 4:
            # 私有IPv4范围
            private_ranges = [
                ipaddress.ip_network('10.0.0.0/8'),
                ipaddress.ip_network('172.16.0.0/12'),
                ipaddress.ip_network('192.168.0.0/16'),
                ipaddress.ip_network('169.254.0.0/16'),  # 链路本地
            ]
            return any(ip in private_range for private_range in private_ranges)
        elif ip.version == 6:
            # 检查ULA（Unique Local Address）fc00::/7和环回地址::1/128
            return ((int(ip) >> 121) == 0b1111110) or (ip == ipaddress.IPv6Address('::1'))
        return False
    except ValueError:
        return False

def should_use_proxy(url):
    """
    决定是否应该对给定的URL使用代理。
    判断依据：
    1. URL是否在PROXY_BYPASS_PATTERNS列表中匹配。
    2. URL的主机名是否为私有IP。
    3. URL的主机名是否为localhost或环回地址。
    如果不满足上述条件，则使用代理。
    """
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        if not hostname:
            # 如果无法解析主机名，默认使用代理
            return True
        
        # 明确检查localhost和环回地址
        if hostname.lower() in ['localhost', 'ip6-localhost']:
            return False

        # 检查是否为环回 IP 地址
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_loopback:
                return False
        except ValueError:
            pass  # 如果不是有效的IP地址，继续其他判断

        # 检查主机名是否匹配PROXY_BYPASS_PATTERNS中的任何模式
        for pattern in PROXY_BYPASS_PATTERNS:
            # 精确匹配
            if hostname == pattern:
                return False
            # 域名/子域名匹配
            if pattern.startswith('.') and hostname.endswith(pattern):
                return False
            # 通配符匹配
            if pattern.startswith('*') and hostname.endswith(pattern[1:]):
                return False
            # IP范围匹配
            try:
                ip = ipaddress.ip_address(hostname)
                network = ipaddress.ip_network(pattern, strict=False)
                if ip in network:
                    return False
            except ValueError:
                pass  # 不是IP地址或无效的网络，继续检查下一个模式
        
        # 检查是否为私有IP
        if is_private_ip(hostname):
            return False
        
        # 如果以上条件都不满足，则使用代理
        return True
    except Exception:
        # 如果解析URL或其他错误，默认使用代理
        return True

# 保存原始 send 方法并应用代理控制的函数
def apply_proxy_control():
    original_send = requests.Session.send

    @functools.wraps(original_send)
    def proxy_aware_send(self, request, **kwargs):
        if not should_use_proxy(request.url):
            kwargs['proxies'] = None
        return original_send(self, request, **kwargs)

    requests.Session.send = proxy_aware_send
