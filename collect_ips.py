import requests
import re
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 目标URL列表
urls_ipv4 = [
    'https://ip.164746.xyz', 
    'https://api.uouin.com/cloudflare.html', 
    'https://www.wetest.vip/page/cloudflare/address_v4.html',
    'https://www.wetest.vip/page/cloudfront/address_v4.html', 
    'https://www.wetest.vip/page/edgeone/address_v4.html', 
    'https://stock.hostmonit.com/CloudFlareYes', 
    'https://stock.hostmonit.com/CloudFlareYesV6', 
    'https://vps789.com/public/sum/cfIpApi' 
]

# 匹配IPv4地址的正则表达式
ipv4_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'

# 删除旧的 ip.txt 文件
if os.path.exists('ip.txt'):
    os.remove('ip.txt')
    print("已删除旧的 ip.txt 文件")

# 用字典存储IP地址和来源，自动去重
ipv4_sources = {}  # ip: source

# 获取IP的国家信息
def get_ip_country(ip: str) -> str:
    """获取IP地址对应的国家"""
    try:
        # 使用 ip-api.com
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country = data.get('country', 'Unknown')
                # 简化国家名称
                if country == 'United States':
                    return 'US'
                elif country == 'United Kingdom':
                    return 'UK'
                elif country == 'China':
                    return 'CN'
                else:
                    return country
    except:
        pass
    
    # 如果失败，根据IP段判断
    if ip.startswith(('104.', '172.', '198.', '162.')):
        return 'Cloudflare'
    elif ip.startswith(('13.', '99.', '205.')):
        return 'AWS'
    else:
        return 'Unknown'

# 获取IP延迟（3次ping，每次间隔1秒，计算平均延迟）
def get_ping_latency(ip: str, num_pings: int = 3, interval: int = 1) -> tuple[str, float]:
    print(f"正在测试IP {ip} 的延迟...")
    latencies = []
    
    for i in range(num_pings):
        try:
            start = time.time()
            # 使用HTTP请求模拟ping，设置较短超时时间
            target_url = f"http://{ip}"
            requests.get(target_url, timeout=5)
            latency = (time.time() - start) * 1000  # 毫秒
            latencies.append(round(latency, 3))
            print(f"  IP {ip} 第 {i+1} 次ping延迟: {latency:.3f}ms")
            if i < num_pings - 1:  # 最后一次不需要sleep
                time.sleep(interval)
        except requests.RequestException as e:
            print(f"  IP {ip} 第 {i+1} 次ping失败: {e}")
            latencies.append(float('inf'))  # 请求失败返回无限延迟
    
    # 计算平均延迟
    avg_latency = sum(latencies) / len(latencies) if latencies else float('inf')
    print(f"IP {ip} 平均延迟: {avg_latency:.3f}ms")
    return ip, avg_latency

# 从URLs抓取IP地址
def fetch_ips(urls, pattern, ip_store):
    print(f"开始从URL抓取IPv4地址...")
    total_ips_found = 0
    
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] 正在从 {url} 获取IPv4...")
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                ips = re.findall(pattern, resp.text)
                
                before_count = len(ip_store)
                source_name = extract_source_name(url)
                
                for ip in ips:
                    ip_store[ip] = source_name
                
                after_count = len(ip_store)
                new_ips = after_count - before_count
                total_ips_found += len(ips)
                print(f"  从 {url} 找到 {len(ips)} 个IPv4，其中 {new_ips} 个是新IPv4")
                print(f"  来源标识: {source_name}")
                
                if ips:
                    print(f"  示例IP: {ips[:3]}")
            else:
                print(f"  请求失败，状态码: {resp.status_code}")
        except requests.RequestException as e:
            print(f"  警告: 获取IPv4失败，URL: {url}, 错误: {e}")
    
    print(f"IPv4抓取完成，总共找到 {total_ips_found} 个IPv4地址，去重后剩余 {len(ip_store)} 个唯一IPv4")

# 从URL中提取有意义的来源名称
def extract_source_name(url: str) -> str:
    """从URL中提取简短的来源名称"""
    if '164746' in url:
        return 'ip164746'
    elif '090227' in url:
        return 'cf090227'
    elif 'hostmonit' in url:
        return 'hostmonit'
    elif 'wetest' in url:
        return 'wetest'
    elif 'uouin' in url:
        return 'uouin'
    elif 'vps789' in url:
        return 'vps789'
    else:
        domain = re.search(r'https?://([^/]+)', url)
        if domain:
            main_domain = domain.group(1).split('.')[-2]
            return main_domain
        return 'unknown'

# 并发获取延迟和国家信息
def fetch_ip_delays_and_countries(ip_store) -> dict:
    if not ip_store:
        print(f"没有找到IPv4地址进行延迟测试")
        return {}
        
    print(f"\n开始测试 {len(ip_store)} 个IPv4的延迟和国家信息...")
    ip_info = {}  # ip: {'latency': float, 'country': str}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 先获取所有IP的延迟
        latency_futures = {executor.submit(get_ping_latency, ip): ip for ip in ip_store.keys()}
        
        completed_count = 0
        for future in as_completed(latency_futures):
            ip, latency = future.result()
            ip_info[ip] = {
                'latency': latency,
                'country': 'Pending'
            }
            completed_count += 1
            print(f"[{completed_count}/{len(ip_store)}] 已完成IPv4 {ip} 延迟测试: {latency:.3f}ms")
    
    # 然后获取国家信息
    print(f"\n开始获取IP国家信息...")
    country_futures = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        for ip in ip_info.keys():
            future = executor.submit(get_ip_country, ip)
            country_futures[future] = ip
        
        completed_count = 0
        for future in as_completed(country_futures):
            ip = country_futures[future]
            country = future.result()
            ip_info[ip]['country'] = country
            completed_count += 1
            latency = ip_info[ip]['latency']
            print(f"[{completed_count}/{len(ip_info)}] 已完成 {ip} - 延迟: {latency:.3f}ms - 国家: {country}")
    
    print(f"所有IPv4测试完成，共测试 {len(ip_info)} 个IPv4")
    return ip_info

# 合并保存所有IP到一个文件
def save_all_ips_to_file(ipv4_info, ipv4_sources, filename):
    all_ips = []
    
    # 处理IPv4地址
    if ipv4_info:
        valid_ipv4 = {ip: info for ip, info in ipv4_info.items() if info['latency'] != float('inf')}
        for ip, info in valid_ipv4.items():
            source = ipv4_sources.get(ip, 'unknown')
            all_ips.append((ip, info['latency'], source, "IPv4", info['country']))
    
    if not all_ips:
        print("错误: 所有IP测试均失败，未找到有效的IP地址")
        return
    
    # 按延迟升序排列
    sorted_ips = sorted(all_ips, key=lambda x: x[1])
    
    print(f"\n排序后的IP列表 (共 {len(sorted_ips)} 个):")
    
    for i, (ip, latency, source, ip_type, country) in enumerate(sorted_ips, 1):
        if latency == float('inf'):
            print(f"{i}. {ip} - 延迟: 未测试 - 国家: {country} - 类型: {ip_type} - 来源: {source}")
        else:
            print(f"{i}. {ip} - 平均延迟: {latency:.3f}ms - 国家: {country} - 类型: {ip_type} - 来源: {source}")
    
    # 写入文件，包含国家信息
    with open(filename, 'w') as f:
        for ip, latency, source, ip_type, country in sorted_ips:
            if latency != float('inf'):
                f.write(f'{ip} #{country}\n')
    
    print(f'\n已保存 {len([ip for ip in sorted_ips if ip[1] != float("inf")])} 个IP到 {filename}')
    print(f'格式: IP #国家')

# 主流程
print("=== Cloudflare IP收集工具开始运行 ===")

# 获取IPv4地址
fetch_ips(urls_ipv4, ipv4_pattern, ipv4_sources)

if not ipv4_sources:
    print("错误: 未找到任何IP地址，程序退出")
    exit(1)

# 处理IPv4地址（延迟和国家信息）
ipv4_info = {}
if ipv4_sources:
    ipv4_info = fetch_ip_delays_and_countries(ipv4_sources)
else:
    print("未找到IPv4地址")

# 只显示延迟最低的前50个IP地址
if ipv4_info:
    valid_ips = {ip: info for ip, info in ipv4_info.items() if info['latency'] != float('inf')}
    top_ips = sorted(valid_ips.items(), key=lambda x: x[1]['latency'])[:50]
    print(f"\n延迟最低的前50个IP地址:")
    for i, (ip, info) in enumerate(top_ips, 1):
        source = ipv4_sources.get(ip, 'unknown')
        print(f"{i}. {ip} - 延迟: {info['latency']:.3f}ms - 国家: {info['country']} - 来源: {source}")

# 合并保存所有IP到一个文件
save_all_ips_to_file(ipv4_info, ipv4_sources, 'ip.txt')

print("\n=== IP收集完成 ===")            latencies.append(round(latency, 3))
            print(f"  IP {ip} 第 {i+1} 次ping延迟: {latency:.3f}ms")
            if i < num_pings - 1:  # 最后一次不需要sleep
                time.sleep(interval)
        except requests.RequestException as e:
            print(f"  IP {ip} 第 {i+1} 次ping失败: {e}")
            latencies.append(float('inf'))  # 请求失败返回无限延迟
    
    # 计算平均延迟
    avg_latency = sum(latencies) / len(latencies) if latencies else float('inf')
    print(f"IP {ip} 平均延迟: {avg_latency:.3f}ms")
    return ip, avg_latency

# 从URLs抓取IP地址，避免无效请求并提高异常处理
def fetch_ips(urls, pattern, ip_store):
    print(f"开始从URL抓取IPv4地址...")
    total_ips_found = 0
    
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] 正在从 {url} 获取IPv4...")
        try:
            # 延长超时时间到15秒
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                ips = re.findall(pattern, resp.text)
                
                before_count = len(ip_store)
                
                # 提取来源名称（从URL中提取有意义的名称）
                source_name = extract_source_name(url)
                
                for ip in ips:
                    ip_store[ip] = source_name
                
                after_count = len(ip_store)
                new_ips = after_count - before_count
                total_ips_found += len(ips)
                print(f"  从 {url} 找到 {len(ips)} 个IPv4，其中 {new_ips} 个是新IPv4")
                print(f"  来源标识: {source_name}")
                
                # 显示找到的部分IP示例
                if ips:
                    print(f"  示例IP: {ips[:3]}")  # 显示前3个作为示例
            else:
                print(f"  请求失败，状态码: {resp.status_code}")
        except requests.RequestException as e:
            print(f"  警告: 获取IPv4失败，URL: {url}, 错误: {e}")
    
    print(f"IPv4抓取完成，总共找到 {total_ips_found} 个IPv4地址，去重后剩余 {len(ip_store)} 个唯一IPv4")

# 从URL中提取有意义的来源名称
def extract_source_name(url: str) -> str:
    """从URL中提取简短的来源名称"""
    if '164746' in url:
        return 'ip164746'
    elif '090227' in url:
        return 'cf090227'
    elif 'hostmonit' in url:
        return 'hostmonit'
    elif 'wetest' in url:
        return 'wetest'
    elif 'uouin' in url:
        return 'uouin'
    elif 'vps789' in url:
        return 'vps789'
    else:
        # 如果都不匹配，使用域名的主要部分
        domain = re.search(r'https?://([^/]+)', url)
        if domain:
            main_domain = domain.group(1).split('.')[-2]  # 获取主域名部分
            return main_domain
        return 'unknown'

# 并发获取延迟和国家信息
def fetch_ip_delays_and_countries(ip_store) -> dict:
    if not ip_store:
        print(f"没有找到IPv4地址进行延迟测试")
        return {}
        
    print(f"\n开始测试 {len(ip_store)} 个IPv4的延迟和国家信息...")
    ip_info = {}  # ip: {'latency': float, 'country': str}
    
    with ThreadPoolExecutor(max_workers=5) as executor:  # 减少并发数避免API限制
        # 先获取所有IP的延迟
        latency_futures = {executor.submit(get_ping_latency, ip): ip for ip in ip_store.keys()}
        
        completed_count = 0
        for future in as_completed(latency_futures):
            ip, latency = future.result()
            ip_info[ip] = {
                'latency': latency,
                'country': 'Pending'  # 先标记为待处理
            }
            completed_count += 1
            print(f"[{completed_count}/{len(ip_store)}] 已完成IPv4 {ip} 延迟测试: {latency:.3f}ms")
    
    # 然后批量获取国家信息（减少并发）
    print(f"\n开始获取IP国家信息...")
    country_futures = {}
    with ThreadPoolExecutor(max_workers=3) as executor:  # 进一步减少并发
        for ip in ip_info.keys():
            future = executor.submit(get_ip_country, ip)
            country_futures[future] = ip
        
        completed_count = 0
        for future in as_completed(country_futures):
            ip = country_futures[future]
            country = future.result()
            ip_info[ip]['country'] = country
            completed_count += 1
            latency = ip_info[ip]['latency']
            print(f"[{completed_count}/{len(ip_info)}] 已完成 {ip} - 延迟: {latency:.3f}ms - 国家: {country}")
    
    print(f"所有IPv4测试完成，共测试 {len(ip_info)} 个IPv4")
    return ip_info

# 合并保存所有IP到一个文件
def save_all_ips_to_file(ipv4_info, ipv4_sources, filename):
    all_ips = []
    
    # 处理IPv4地址
    if ipv4_info:
        valid_ipv4 = {ip: info for ip, info in ipv4_info.items() if info['latency'] != float('inf')}
        for ip, info in valid_ipv4.items():
            source = ipv4_sources.get(ip, 'unknown')
            all_ips.append((ip, info['latency'], source, "IPv4", info['country']))
    
    if not all_ips:
        print("错误: 所有IP测试均失败，未找到有效的IP地址")
        return
    
    # 按延迟升序排列
    sorted_ips = sorted(all_ips, key=lambda x: x[1])
    
    print(f"\n排序后的IP列表 (共 {len(sorted_ips)} 个):")
    
    for i, (ip, latency, source, ip_type, country) in enumerate(sorted_ips, 1):
        if latency == float('inf'):
            print(f"{i}. {ip} - 延迟: 未测试 - 国家: {country} - 类型: {ip_type} - 来源: {source}")
        else:
            print(f"{i}. {ip} - 平均延迟: {latency:.3f}ms - 国家: {country} - 类型: {ip_type} - 来源: {source}")
    
    # 写入文件，包含国家信息
    with open(filename, 'w') as f:
        for ip, latency, source, ip_type, country in sorted_ips:
            if latency != float('inf'):  # 只保存测试成功的IP
                f.write(f'{ip} #{country}\n')  # IP地址后面加上国家
    
    print(f'\n已保存 {len([ip for ip in sorted_ips if ip[1] != float("inf")])} 个IP到 {filename}')
    print(f'格式: IP #国家')

# 主流程
print("=== Cloudflare IP收集工具开始运行 ===")

# 获取IPv4地址
fetch_ips(urls_ipv4, ipv4_pattern, ipv4_sources)

if not ipv4_sources:
    print("错误: 未找到任何IP地址，程序退出")
    exit(1)

# 处理IPv4地址（延迟和国家信息）
ipv4_info = {}
if ipv4_sources:
    ipv4_info = fetch_ip_delays_and_countries(ipv4_sources)
else:
    print("未找到IPv4地址")

# 只显示延迟最低的前50个IP地址
if ipv4_info:
    # 过滤掉延迟为无限的IP，然后排序取前50
    valid_ips = {ip: info for ip, info in ipv4_info.items() if info['latency'] != float('inf')}
    top_ips = sorted(valid_ips.items(), key=lambda x: x[1]['latency'])[:50]
    print(f"\n延迟最低的前50个IP地址:")
    for i, (ip, info) in enumerate(top_ips, 1):
        source = ipv4_sources.get(ip, 'unknown')
        print(f"{i}. {ip} - 延迟: {info['latency']:.3f}ms - 国家: {info['country']} - 来源: {source}")

# 合并保存所有IP到一个文件
save_all_ips_to_file(ipv4_info, ipv4_sources, 'ip.txt')

print("\n=== IP收集完成 ===")            # 使用HTTP请求模拟ping，设置较短超时时间
            target_url = f"http://{ip}"
            
            requests.get(target_url, timeout=5)
            latency = (time.time() - start) * 1000  # 毫秒
            latencies.append(round(latency, 3))
            print(f"  IP {ip} 第 {i+1} 次ping延迟: {latency:.3f}ms")
            if i < num_pings - 1:  # 最后一次不需要sleep
                time.sleep(interval)
        except requests.RequestException as e:
            print(f"  IP {ip} 第 {i+1} 次ping失败: {e}")
            latencies.append(float('inf'))  # 请求失败返回无限延迟
    
    # 计算平均延迟
    avg_latency = sum(latencies) / len(latencies) if latencies else float('inf')
    print(f"IP {ip} 平均延迟: {avg_latency:.3f}ms")
    return ip, avg_latency

# 从URLs抓取IP地址，避免无效请求并提高异常处理
def fetch_ips(urls, pattern, ip_store):
    print(f"开始从URL抓取IPv4地址...")
    total_ips_found = 0
    
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] 正在从 {url} 获取IPv4...")
        try:
            # 延长超时时间到15秒
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                ips = re.findall(pattern, resp.text)
                
                before_count = len(ip_store)
                
                # 提取来源名称（从URL中提取有意义的名称）
                source_name = extract_source_name(url)
                
                for ip in ips:
                    ip_store[ip] = source_name
                
                after_count = len(ip_store)
                new_ips = after_count - before_count
                total_ips_found += len(ips)
                print(f"  从 {url} 找到 {len(ips)} 个IPv4，其中 {new_ips} 个是新IPv4")
                print(f"  来源标识: {source_name}")
                
                # 显示找到的部分IP示例
                if ips:
                    print(f"  示例IP: {ips[:3]}")  # 显示前3个作为示例
            else:
                print(f"  请求失败，状态码: {resp.status_code}")
        except requests.RequestException as e:
            print(f"  警告: 获取IPv4失败，URL: {url}, 错误: {e}")
    
    print(f"IPv4抓取完成，总共找到 {total_ips_found} 个IPv4地址，去重后剩余 {len(ip_store)} 个唯一IPv4")

# 从URL中提取有意义的来源名称
def extract_source_name(url: str) -> str:
    """从URL中提取简短的来源名称"""
    if '164746' in url:
        return 'ip164746'
    elif '090227' in url:
        return 'cf090227'
    elif 'hostmonit' in url:
        return 'hostmonit'
    elif 'wetest' in url:
        return 'wetest'
    elif 'uouin' in url:
        return 'uouin'
    elif 'vps789' in url:
        return 'vps789'
    else:
        # 如果都不匹配，使用域名的主要部分
        domain = re.search(r'https?://([^/]+)', url)
        if domain:
            main_domain = domain.group(1).split('.')[-2]  # 获取主域名部分
            return main_domain
        return 'unknown'

# 并发获取延迟和国家信息
def fetch_ip_delays_and_countries(ip_store) -> dict:
    if not ip_store:
        print(f"没有找到IPv4地址进行延迟测试")
        return {}
        
    print(f"\n开始测试 {len(ip_store)} 个IPv4的延迟和国家信息...")
    ip_info = {}  # ip: {'latency': float, 'country': str}
    
    with ThreadPoolExecutor(max_workers=5) as executor:  # 减少并发数避免API限制
        # 先获取所有IP的延迟
        latency_futures = {executor.submit(get_ping_latency, ip): ip for ip in ip_store.keys()}
        
        completed_count = 0
        for future in as_completed(latency_futures):
            ip, latency = future.result()
            ip_info[ip] = {
                'latency': latency,
                'country': 'Pending'  # 先标记为待处理
            }
            completed_count += 1
            print(f"[{completed_count}/{len(ip_store)}] 已完成IPv4 {ip} 延迟测试: {latency:.3f}ms")
    
    # 然后批量获取国家信息（减少并发）
    print(f"\n开始获取IP国家信息...")
    country_futures = {}
    with ThreadPoolExecutor(max_workers=3) as executor:  # 进一步减少并发
        for ip in ip_info.keys():
            future = executor.submit(get_ip_country, ip)
            country_futures[future] = ip
        
        completed_count = 0
        for future in as_completed(country_futures):
            ip = country_futures[future]
            country = future.result()
            ip_info[ip]['country'] = country
            completed_count += 1
            latency = ip_info[ip]['latency']
            print(f"[{completed_count}/{len(ip_info)}] 已完成 {ip} - 延迟: {latency:.3f}ms - 国家: {country}")
    
    print(f"所有IPv4测试完成，共测试 {len(ip_info)} 个IPv4")
    return ip_info

# 合并保存所有IP到一个文件
def save_all_ips_to_file(ipv4_info, ipv4_sources, filename):
    all_ips = []
    
    # 处理IPv4地址
    if ipv4_info:
        valid_ipv4 = {ip: info for ip, info in ipv4_info.items() if info['latency'] != float('inf')}
        for ip, info in valid_ipv4.items():
            source = ipv4_sources.get(ip, 'unknown')
            all_ips.append((ip, info['latency'], source, "IPv4", info['country']))
    
    if not all_ips:
        print("错误: 所有IP测试均失败，未找到有效的IP地址")
        return
    
    # 按延迟升序排列
    sorted_ips = sorted(all_ips, key=lambda x: x[1])
    
    print(f"\n排序后的IP列表 (共 {len(sorted_ips)} 个):")
    
    for i, (ip, latency, source, ip_type, country) in enumerate(sorted_ips, 1):
        if latency == float('inf'):
            print(f"{i}. {ip} - 延迟: 未测试 - 国家: {country} - 类型: {ip_type} - 来源: {source}")
        else:
            print(f"{i}. {ip} - 平均延迟: {latency:.3f}ms - 国家: {country} - 类型: {ip_type} - 来源: {source}")
    
    # 写入文件，包含国家信息
    with open(filename, 'w') as f:
        for ip, latency, source, ip_type, country in sorted_ips:
            if latency != float('inf'):  # 只保存测试成功的IP
                f.write(f'{ip} #{country}\n')  # IP地址后面加上国家
    
    print(f'\n已保存 {len([ip for ip in sorted_ips if ip[1] != float("inf")])} 个IP到 {filename}')
    print(f'格式: IP #国家')

# 主流程
print("=== Cloudflare IP收集工具开始运行 ===")

# 获取IPv4地址
fetch_ips(urls_ipv4, ipv4_pattern, ipv4_sources)

if not ipv4_sources:
    print("错误: 未找到任何IP地址，程序退出")
    exit(1)

# 处理IPv4地址（延迟和国家信息）
ipv4_info = {}
if ipv4_sources:
    ipv4_info = fetch_ip_delays_and_countries(ipv4_sources)
else:
    print("未找到IPv4地址")

# 只显示延迟最低的前50个IP地址
if ipv4_info:
    # 过滤掉延迟为无限的IP，然后排序取前50
    valid_ips = {ip: info for ip, info in ipv4_info.items() if info['latency'] != float('inf')}
    top_ips = sorted(valid_ips.items(), key=lambda x: x[1]['latency'])[:50]
    print(f"\n延迟最低的前50个IP地址:")
    for i, (ip, info) in enumerate(top_ips, 1):
        source = ipv4_sources.get(ip, 'unknown')
        print(f"{i}. {ip} - 延迟: {info['latency']:.3f}ms - 国家: {info['country']} - 来源: {source}")

# 合并保存所有IP到一个文件
save_all_ips_to_file(ipv4_info, ipv4_sources, 'ip.txt')

print("\n=== IP收集完成 ===")                
                for ip in ips:
                    ip_store[ip] = source_name
                
                after_count = len(ip_store)
                new_ips = after_count - before_count
                total_ips_found += len(ips)
                print(f"  从 {url} 找到 {len(ips)} 个IPv4，其中 {new_ips} 个是新IPv4")
                print(f"  来源标识: {source_name}")
                
                # 显示找到的部分IP示例
                if ips:
                    print(f"  示例IP: {ips[:3]}")  # 显示前3个作为示例
            else:
                print(f"  请求失败，状态码: {resp.status_code}")
        except requests.RequestException as e:
            print(f"  警告: 获取IPv4失败，URL: {url}, 错误: {e}")
    
    print(f"IPv4抓取完成，总共找到 {total_ips_found} 个IPv4地址，去重后剩余 {len(ip_store)} 个唯一IPv4")

# 从URL中提取有意义的来源名称
def extract_source_name(url: str) -> str:
    """从URL中提取简短的来源名称"""
    if '164746' in url:
        return 'ip164746'
    elif '090227' in url:
        return 'cf090227'
    elif 'hostmonit' in url:
        return 'hostmonit'
    elif 'wetest' in url:
        return 'wetest'
    elif 'uouin' in url:
        return 'uouin'
    elif 'vps789' in url:
        return 'vps789'
    else:
        # 如果都不匹配，使用域名的主要部分
        domain = re.search(r'https?://([^/]+)', url)
        if domain:
            main_domain = domain.group(1).split('.')[-2]  # 获取主域名部分
            return main_domain
        return 'unknown'

# 并发获取延迟和国家信息
def fetch_ip_delays_and_countries(ip_store) -> dict:
    if not ip_store:
        print(f"没有找到IPv4地址进行延迟测试")
        return {}
        
    print(f"\n开始测试 {len(ip_store)} 个IPv4的延迟和国家信息...")
    ip_info = {}  # ip: {'latency': float, 'country': str}
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 提交延迟测试任务
        latency_futures = {executor.submit(get_ping_latency, ip): ip for ip in ip_store.keys()}
        
        completed_count = 0
        for future in as_completed(latency_futures):
            ip, latency = future.result()
            
            # 获取国家信息
            print(f"  正在获取IP {ip} 的国家信息...")
            country = get_ip_country(ip)
            
            ip_info[ip] = {
                'latency': latency,
                'country': country
            }
            
            completed_count += 1
            print(f"[{completed_count}/{len(ip_store)}] 已完成IPv4 {ip} - 延迟: {latency:.3f}ms - 国家: {country}")
    
    print(f"所有IPv4测试完成，共测试 {len(ip_info)} 个IPv4")
    return ip_info

# 合并保存所有IP到一个文件
def save_all_ips_to_file(ipv4_info, ipv4_sources, filename):
    all_ips = []
    
    # 处理IPv4地址
    if ipv4_info:
        valid_ipv4 = {ip: info for ip, info in ipv4_info.items() if info['latency'] != float('inf')}
        for ip, info in valid_ipv4.items():
            source = ipv4_sources.get(ip, 'unknown')
            all_ips.append((ip, info['latency'], source, "IPv4", info['country']))
    
    if not all_ips:
        print("错误: 所有IP测试均失败，未找到有效的IP地址")
        return
    
    # 按延迟升序排列
    sorted_ips = sorted(all_ips, key=lambda x: x[1])
    
    print(f"\n排序后的IP列表 (共 {len(sorted_ips)} 个):")
    
    for i, (ip, latency, source, ip_type, country) in enumerate(sorted_ips, 1):
        if latency == float('inf'):
            print(f"{i}. {ip} - 延迟: 未测试 - 国家: {country} - 类型: {ip_type} - 来源: {source}")
        else:
            print(f"{i}. {ip} - 平均延迟: {latency:.3f}ms - 国家: {country} - 类型: {ip_type} - 来源: {source}")
    
    # 写入文件，包含国家信息
    with open(filename, 'w') as f:
        for ip, latency, source, ip_type, country in sorted_ips:
            if latency != float('inf'):  # 只保存测试成功的IP
                f.write(f'{ip} #{country}\n')  # IP地址后面加上国家
    
    print(f'\n已保存 {len([ip for ip in sorted_ips if ip[1] != float("inf")])} 个IP到 {filename}')
    print(f'格式: IP #国家')

# 主流程
print("=== Cloudflare IP收集工具开始运行 ===")

# 获取IPv4地址
fetch_ips(urls_ipv4, ipv4_pattern, ipv4_sources)

if not ipv4_sources:
    print("错误: 未找到任何IP地址，程序退出")
    exit(1)

# 处理IPv4地址（延迟和国家信息）
ipv4_info = {}
if ipv4_sources:
    ipv4_info = fetch_ip_delays_and_countries(ipv4_sources)
else:
    print("未找到IPv4地址")

# 只显示延迟最低的前50个IP地址
if ipv4_info:
    # 过滤掉延迟为无限的IP，然后排序取前50
    valid_ips = {ip: info for ip, info in ipv4_info.items() if info['latency'] != float('inf')}
    top_ips = sorted(valid_ips.items(), key=lambda x: x[1]['latency'])[:50]
    print(f"\n延迟最低的前50个IP地址:")
    for i, (ip, info) in enumerate(top_ips, 1):
        source = ipv4_sources.get(ip, 'unknown')
        print(f"{i}. {ip} - 延迟: {info['latency']:.3f}ms - 国家: {info['country']} - 来源: {source}")

# 合并保存所有IP到一个文件
save_all_ips_to_file(ipv4_info, ipv4_sources, 'ip.txt')

print("\n=== IP收集完成 ===")
