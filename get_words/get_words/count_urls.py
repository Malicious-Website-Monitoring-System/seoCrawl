# count_url.py

import re

def load_hosts(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        hosts = file.read().strip().split('\n')
    return hosts

def count_urls(file_path):
    url_count = {}
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = re.match(r'(https?://[^\s]+)', line)
            if match:
                url = match.group(1)
                if url in url_count:
                    url_count[url] += 1
                else:
                    url_count[url] = 1
    
    return url_count

def main():
    hosts_file_path = 'hosts.txt'   # hosts.txt 파일 경로
    input_file_path = 'divide.txt'  # divide.txt 파일 경로
    output_file_path = 'a.txt'      # a.txt 파일 경로

    hosts = load_hosts(hosts_file_path)
    url_count = count_urls(input_file_path)
    
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        total_urls = len(url_count)
        output_file.write(f"Total unique URLs: {total_urls}\n")
        output_file.write("\nURL counts:\n")
        for host in hosts:
            count = url_count.get(host, 0)
            output_file.write(f"{host} ---> {count}\n")
    
    print(f"Results have been written to {output_file_path}")

if __name__ == "__main__":
    main()