import requests
from bs4 import BeautifulSoup
import re
import os
import time

# 目标URL
url = 'https://abalone.webn.cc/kk/bestip'

# IP地址正则表达式
ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'

# 验证IP地址是否有效
def is_valid_ip(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or not 0 <= int(part) <= 255:
            return False
    # 排除私有IP和内网IP
    if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.') or ip.startswith('127.'):
        return False
    return True

# 测试IP的延迟和可用性（针对中国网络优化）
def test_ip_latency(ip, timeout=3):
    """测试IP的延迟"""
    try:
        start_time = time.time()
        response = requests.get(f'http://{ip}', timeout=timeout, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        latency = int((time.time() - start_time) * 1000)  # 转换为毫秒
        return latency, response.status_code == 200
    except:
        return None, False

# 检查ip.txt文件是否存在,如果存在则删除它
if os.path.exists('ip.txt'):
    os.remove('ip.txt')

# 设置请求头，模拟中国地区用户访问
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}

print('开始从网站提取IP地址...')
print(f'目标网站: {url}')

# 存储所有找到的IP
all_ips = set()

try:
    # 发送HTTP请求获取网页内容
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 查找包含IP地址的各种元素
    elements = soup.find_all(['div', 'span', 'p', 'td', 'li', 'pre', 'code'])
    
    # 也检查整个页面的文本内容
    page_text = soup.get_text()
    
    ip_count = 0
    # 从元素中提取IP
    for element in elements:
        element_text = element.get_text()
        ip_matches = re.findall(ip_pattern, element_text)
        
        for ip in ip_matches:
            if is_valid_ip(ip):
                all_ips.add(ip)
                ip_count += 1
    
    # 从整个页面文本中提取IP（作为补充）
    ip_matches = re.findall(ip_pattern, page_text)
    for ip in ip_matches:
        if is_valid_ip(ip):
            all_ips.add(ip)
    
    print(f'从网站提取了 {len(all_ips)} 个有效IP地址')
    
except Exception as e:
    print(f'处理网站时发生错误: {e}')
    # 如果无法访问网站，使用一些常见的中国优化IP作为备选
    fallback_ips = [
        '1.0.0.1', '1.1.1.1', '8.8.8.8', '8.8.4.4',
        '180.76.76.76', '119.29.29.29', '114.114.114.114'
    ]
    all_ips.update(fallback_ips)
    print(f'使用备用IP列表: {len(all_ips)} 个IP')

# 创建中国优化的IP列表
print('\n开始测试IP延迟（针对中国网络优化）...')

# 存储测试结果
ip_results = []

# 测试每个IP的延迟
tested_count = 0
for ip in all_ips:
    try:
        latency, is_accessible = test_ip_latency(ip)
        if latency is not None:
            status = "可用" if is_accessible else "不可访问"
            ip_results.append({
                'ip': ip,
                'latency': latency,
                'status': status,
                'accessible': is_accessible
            })
            print(f'测试: {ip} - 延迟: {latency}ms - {status}')
        else:
            ip_results.append({
                'ip': ip,
                'latency': None,
                'status': '超时',
                'accessible': False
            })
            print(f'测试: {ip} - 超时')
    except Exception as e:
        print(f'测试 {ip} 时出错: {e}')
    
    tested_count += 1
    # 短暂延迟避免请求过快
    time.sleep(0.1)

# 根据延迟排序，优先选择低延迟的IP
available_ips = [ip for ip in ip_results if ip['accessible']]
available_ips.sort(key=lambda x: x['latency'] if x['latency'] is not None else float('inf'))

unavailable_ips = [ip for ip in ip_results if not ip['accessible']]

print(f'\n测试完成!')
print(f'总IP数量: {len(ip_results)}')
print(f'可用IP数量: {len(available_ips)}')
print(f'不可用IP数量: {len(unavailable_ips)}')

# 将结果保存到文件
with open('ip.txt', 'w', encoding='utf-8') as file:
    file.write('# 中国优化IP列表 - 按延迟排序\n')
    file.write('# 格式: IP#延迟(ms)#状态\n')
    file.write('# 生成时间: ' + time.strftime('%Y-%m-%d %H:%M:%S') + '\n\n')
    
    # 先写入可用的IP（按延迟排序）
    if available_ips:
        file.write('# === 可用IP (按延迟排序) ===\n')
        for ip_info in available_ips:
            file.write(f"{ip_info['ip']}#{ip_info['latency']}ms#{ip_info['status']}\n")
    
    # 再写入不可用的IP
    if unavailable_ips:
        file.write('\n# === 不可用IP ===\n')
        for ip_info in unavailable_ips:
            latency_str = '超时' if ip_info['latency'] is None else f"{ip_info['latency']}ms"
            file.write(f"{ip_info['ip']}#{latency_str}#{ip_info['status']}\n")

print('\nIP地址列表已保存到ip.txt文件中。')

# 显示最佳IP推荐
if available_ips:
    best_ip = available_ips[0]
    print(f'\n⭐ 推荐使用的最佳IP: {best_ip["ip"]}')
    print(f'   延迟: {best_ip["latency"]}ms')
    print(f'   状态: {best_ip["status"]}')
    
    # 显示前5个最佳IP
    print(f'\n🏆 前5个最佳IP:')
    for i, ip_info in enumerate(available_ips[:5]):
        print(f'   {i+1}. {ip_info["ip"]} - {ip_info["latency"]}ms')

# 生成用于CMCC网络的特别推荐
print(f'\n📡 中国移动网络推荐IP:')
cmcc_recommended = [ip for ip in available_ips if any([
    ip['ip'].startswith('211.138.'),
    ip['ip'].startswith('211.136.'),
    ip['ip'].startswith('211.137.'),
    ip['ip'].startswith('218.200.'),
    ip['ip'].startswith('218.201.')
])]

if cmcc_recommended:
    for ip_info in cmcc_recommended[:3]:
        print(f'   {ip_info["ip"]} - {ip_info["latency"]}ms')
else:
    print('   未找到特定运营商优化IP，使用通用推荐')
    for ip_info in available_ips[:3]:
        print(f'   {ip_info["ip"]} - {ip_info["latency"]}ms')
