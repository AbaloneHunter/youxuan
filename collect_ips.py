import requests
from bs4 import BeautifulSoup
import re
import os
import time
import random
from urllib.parse import urlparse
import ipaddress
import subprocess
import sys

# 目标URL列表
urls = [
    'https://www.wetest.vip/page/cloudflare/address_v4.html', 
    'https://ip.164746.xyz'
]

# 更严格的IP地址正则表达式
ip_pattern = r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'

# 国家代码到国旗的映射
COUNTRY_FLAGS = {
    'CN': '❣️', 'TW': '❣️',
    'US': '🇺🇸', 'SG': '🇸🇬', 'JP': '🇯🇵', 'HK': '❣️', 'KR': '🇰🇷',
    'DE': '🇩🇪', 'GB': '🇬🇧', 'FR': '🇫🇷', 'CA': '🇨🇦', 'AU': '🇦🇺',
    'NL': '🇳🇱', 'SE': '🇸🇪', 'FI': '🇫🇮', 'NO': '🇳🇴', 'DK': '🇩🇰',
    'CH': '🇨🇭', 'IT': '🇮🇹', 'ES': '🇪🇸', 'PT': '🇵🇹', 'BE': '🇧🇪',
    'AT': '🇦🇹', 'IE': '🇮🇪', 'PL': '🇵🇱', 'CZ': '🇨🇿', 'HU': '🇭🇺',
    'RO': '🇷🇴', 'BG': '🇧🇬', 'GR': '🇬🇷', 'TR': '🇹🇷', 'RU': '🇷🇺',
    'UA': '🇺🇦', 'IL': '🇮🇱', 'AE': '🇦🇪', 'SA': '🇸🇦', 'IN': '🇮🇳',
    'TH': '🇹🇭', 'MY': '🇲🇾', 'ID': '🇮🇩', 'VN': '🇻🇳', 'PH': '🇵🇭',
    'BR': '🇧🇷', 'MX': '🇲🇽', 'AR': '🇦🇷', 'CL': '🇨🇱', 'CO': '🇨🇴',
    'ZA': '🇿🇦', 'EG': '🇪🇬', 'NG': '🇳🇬', 'KE': '🇰🇪',
    'UN': '🏴'
}

# 国家代码到中文名称的映射
COUNTRY_NAMES = {
    'CN': '中·国',
    'TW': '台·湾',
    'US': '美国',
    'SG': '新加坡',
    'JP': '日本',
    'HK': '香·港',
    'KR': '韩国',
    'DE': '德国',
    'GB': '英国',
    'FR': '法国',
    'CA': '加拿大',
    'AU': '澳大利亚',
    'NL': '荷兰',
    'SE': '瑞典',
    'FI': '芬兰',
    'NO': '挪威',
    'DK': '丹麦',
    'CH': '瑞士',
    'IT': '意大利',
    'ES': '西班牙',
    'PT': '葡萄牙',
    'BE': '比利时',
    'AT': '奥地利',
    'IE': '爱尔兰',
    'PL': '波兰',
    'CZ': '捷克',
    'HU': '匈牙利',
    'RO': '罗马尼亚',
    'BG': '保加利亚',
    'GR': '希腊',
    'TR': '土耳其',
    'RU': '俄罗斯',
    'UA': '乌克兰',
    'IL': '以色列',
    'AE': '阿联酋',
    'SA': '沙特',
    'IN': '印度',
    'TH': '泰国',
    'MY': '马来西亚',
    'ID': '印度尼西亚',
    'VN': '越南',
    'PH': '菲律宾',
    'BR': '巴西',
    'MX': '墨西哥',
    'AR': '阿根廷',
    'CL': '智利',
    'CO': '哥伦比亚',
    'ZA': '南非',
    'EG': '埃及',
    'NG': '尼日利亚',
    'KE': '肯尼亚',
    'UN': '未知'
}

# 验证IP地址是否有效
def is_valid_ip(ip):
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False

def get_real_ip_country_code(ip):
    """使用真实的地理位置API检测IP国家代码"""
    apis = [
        {
            'url': f'http://ip-api.com/json/{ip}?fields=status,message,countryCode',
            'field': 'countryCode',
            'check_field': 'status',
            'check_value': 'success'
        },
        {
            'url': f'https://ipapi.co/{ip}/json/',
            'field': 'country_code',
            'check_field': 'country_code',
            'check_value': None
        }
    ]
    
    for api in apis:
        try:
            response = requests.get(api['url'], timeout=3, verify=False)
            if response.status_code == 200:
                data = response.json()
                
                if api['check_value'] is not None:
                    if data.get(api['check_field']) != api['check_value']:
                        continue
                else:
                    if api['check_field'] not in data:
                        continue
                
                country_code = data.get(api['field'])
                if country_code:
                    return country_code
        except Exception:
            continue
    
    return 'UN'

def get_country_display_name(country_code):
    """获取国家显示名称"""
    country_name = COUNTRY_NAMES.get(country_code, country_code)
    return f"{country_name}·{country_code}"

def format_ip_output(ip, country_code, port=443):
    """输出 ip:端口#国旗国家名称·国家代码 格式"""
    flag = COUNTRY_FLAGS.get(country_code, '🏴')
    country_display = get_country_display_name(country_code)
    
    return f"{ip}:{port}#{flag}{country_display}"

def setup_git_config():
    """配置Git用户信息"""
    try:
        print("配置Git用户信息...")
        
        # 配置邮箱
        email_result = subprocess.run(['git', 'config', '--global', 'user.email', 'codger.gg@gmail.com'], 
                                    capture_output=True, text=True, cwd=os.getcwd())
        if email_result.returncode != 0:
            print(f"配置Git邮箱失败: {email_result.stderr}")
            return False
        
        # 配置用户名
        name_result = subprocess.run(['git', 'config', '--global', 'user.name', 'Cloudflare IP Collector'], 
                                   capture_output=True, text=True, cwd=os.getcwd())
        if name_result.returncode != 0:
            print(f"配置Git用户名失败: {name_result.stderr}")
            return False
        
        print("✅ Git用户信息配置成功")
        return True
        
    except Exception as e:
        print(f"配置Git用户信息出错: {e}")
        return False

def run_git_commands():
    """执行Git命令来提交更改"""
    try:
        print("\n" + "="*60)
        print(f"{'自动Git提交':^60}")
        print("="*60)
        
        # 首先配置Git用户信息
        if not setup_git_config():
            print("Git用户信息配置失败，跳过Git提交")
            return
        
        # 检查是否在Git仓库中
        result = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode != 0:
            print("当前目录不是Git仓库，跳过Git提交")
            return
        
        # 检查custom_ips.txt文件是否存在
        if not os.path.exists('custom_ips.txt'):
            print("custom_ips.txt 文件不存在，跳过Git提交")
            return
        
        # 添加所有更改的文件
        print("添加文件到Git暂存区...")
        add_result = subprocess.run(['git', 'add', 'custom_ips.txt'], 
                                  capture_output=True, text=True, cwd=os.getcwd())
        if add_result.returncode != 0:
            print(f"添加文件失败: {add_result.stderr}")
            return
        
        # 检查是否有更改需要提交
        status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                     capture_output=True, text=True, cwd=os.getcwd())
        if not status_result.stdout.strip():
            print("没有需要提交的更改")
            return
        
        print("当前Git状态:")
        status_detailed = subprocess.run(['git', 'status'], 
                                       capture_output=True, text=True, cwd=os.getcwd())
        print(status_detailed.stdout)
        
        # 提交更改
        print("提交更改到Git...")
        commit_result = subprocess.run(['git', 'commit', '-m', '更新Cloudflare IP列表'], 
                                     capture_output=True, text=True, cwd=os.getcwd())
        if commit_result.returncode != 0:
            print(f"提交失败: {commit_result.stderr}")
            return
        
        # 推送到远程仓库
        print("推送到远程仓库...")
        push_result = subprocess.run(['git', 'push', 'origin', 'main'], 
                                   capture_output=True, text=True, cwd=os.getcwd())
        if push_result.returncode == 0:
            print("✅ Git操作完成！文件已提交并推送到远程仓库")
        else:
            print(f"推送失败: {push_result.stderr}")
            
    except Exception as e:
        print(f"Git操作出错: {e}")

# 设置请求头，模拟浏览器访问
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
    'Connection': 'keep-alive',
}

# 创建会话对象
session = requests.Session()
session.headers.update(headers)

def extract_ips_from_text(text):
    """从文本中提取IP地址"""
    ip_matches = re.findall(ip_pattern, text)
    valid_ips = set()
    
    for ip in ip_matches:
        if is_valid_ip(ip):
            valid_ips.add(ip)
    
    return valid_ips

def process_wetest_vip(soup):
    """处理wetest.vip网站"""
    ips = set()
    
    # 尝试多种选择器
    selectors = ['li', 'tr', 'td', 'div']
    
    for selector in selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text(strip=True)
            ips.update(extract_ips_from_text(text))
    
    return ips

def process_164746_xyz(soup):
    """处理164746.xyz网站"""
    ips = set()
    
    # 查找表格中的IP地址
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                text = cell.get_text(strip=True)
                ips.update(extract_ips_from_text(text))
    
    return ips

def process_generic_site(soup):
    """处理通用网站"""
    ips = set()
    
    # 查找所有可能包含IP的元素
    elements = soup.find_all(['li', 'tr', 'td', 'div', 'p', 'span'])
    for element in elements:
        text = element.get_text(strip=True)
        ips.update(extract_ips_from_text(text))
    
    return ips

print("="*60)
print(f"{'Cloudflare IP采集工具 v1.0':^60}")
print("="*60)

# 创建一个集合来存储所有IP地址
all_ips = set()
formatted_ips = []

for url in urls:
    try:
        print(f'正在处理: {url}')
        
        # 随机延迟，避免请求过于频繁
        time.sleep(random.uniform(1, 2))
        
        # 发送HTTP请求获取网页内容
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 根据不同的网站使用不同的处理策略
        if 'wetest.vip' in url:
            ips = process_wetest_vip(soup)
        elif '164746.xyz' in url:
            ips = process_164746_xyz(soup)
        else:
            ips = process_generic_site(soup)
        
        print(f'从 {url} 提取了 {len(ips)} 个IP地址')
        all_ips.update(ips)
        
    except requests.exceptions.RequestException as e:
        print(f'请求 {url} 时出错: {e}')
    except Exception as e:
        print(f'处理 {url} 时发生错误: {e}')

# 为IP地址添加地理位置信息并格式化
if all_ips:
    print(f"\n正在获取IP地理位置信息...")
    
    ip_list = list(all_ips)
    for i, ip in enumerate(ip_list, 1):
        try:
            # 获取国家代码
            country_code = get_real_ip_country_code(ip)
            
            # 格式化输出
            formatted_ip = format_ip_output(ip, country_code)
            formatted_ips.append(formatted_ip)
            
            print(f"处理进度: {i}/{len(ip_list)} - {formatted_ip}")
            
            # 添加延迟避免请求过于频繁
            if i < len(ip_list):
                time.sleep(0.5)
                
        except Exception as e:
            print(f"处理IP {ip} 时出错: {e}")
            # 即使出错也添加默认格式
            formatted_ip = format_ip_output(ip, 'UN')
            formatted_ips.append(formatted_ip)

# 将格式化后的IP地址写入custom_ips.txt文件
if formatted_ips:
    with open('custom_ips.txt', 'w', encoding='utf-8') as file:
        for formatted_ip in formatted_ips:
            file.write(formatted_ip + '\n')
    
    print("\n" + "="*60)
    print(f"{'采集完成':^60}")
    print("="*60)
    print(f'总共采集了 {len(formatted_ips)} 个IP地址')
    print(f'结果已保存到 custom_ips.txt 文件中')
    
    # 显示前10个IP作为示例
    print(f'\n前10个IP地址示例:')
    for i, ip in enumerate(formatted_ips[:10], 1):
        print(f'  {i}. {ip}')
    
    # 显示统计信息
    country_stats = {}
    for ip in formatted_ips:
        # 从格式化字符串中提取国家代码
        for country_code in COUNTRY_FLAGS:
            if f"{COUNTRY_FLAGS[country_code]}{COUNTRY_NAMES.get(country_code, '')}·{country_code}" in ip:
                country_stats[country_code] = country_stats.get(country_code, 0) + 1
                break
    
    print(f'\nIP地址分布统计:')
    for country_code, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True):
        country_name = COUNTRY_NAMES.get(country_code, country_code)
        print(f'  {COUNTRY_FLAGS.get(country_code, "🏴")} {country_name}: {count}个')
    
    # 自动执行Git命令
    run_git_commands()
    
else:
    print('没有采集到任何有效的IP地址')

print("="*60)    # 自动执行Git命令
    run_git_commands()
    
else:
    print('没有采集到任何有效的IP地址')

print("="*60)
