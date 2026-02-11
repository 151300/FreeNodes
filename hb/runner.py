#!/usr/bin/env python3
"""
hb/runner.py - 节点处理系统执行器
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from datetime import datetime
import time
import hashlib

class NodeProcessor:
    def __init__(self, config_dir="hb"):
        """初始化处理器"""
        self.base_dir = Path(config_dir)
        self.config = self.load_config()
        
        # 初始化目录
        self.init_directories()
        
        # 设置日志
        self.setup_logging()
        
        self.logger = logging.getLogger(__name__)
        
    def load_config(self):
        """加载配置"""
        config_files = {
            'main': 'config.yml',
            'tasks': 'tasks.yml',
            'triggers': 'triggers.yml',
            'secrets': 'secrets.yml'  # 注意：不提交到版本控制
        }
        
        config = {}
        for key, filename in config_files.items():
            filepath = self.base_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    config[key] = yaml.safe_load(f)
            else:
                config[key] = {}
                
        return config
    
    def init_directories(self):
        """初始化目录结构"""
        dirs = self.config.get('main', {}).get('directories', {})
        
        for key, rel_path in dirs.items():
            # 处理相对路径
            if rel_path.startswith('./'):
                full_path = self.base_dir / rel_path[2:]
            elif rel_path.startswith('../'):
                full_path = self.base_dir.parent / rel_path[3:]
            else:
                full_path = self.base_dir / rel_path
                
            full_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"创建目录: {full_path}")
            
    def setup_logging(self):
        """设置日志"""
        log_config = self.config.get('main', {}).get('logging', {})
        
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = self.base_dir / log_config.get('file', 'hb_processing.log')
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
    def calculate_hash(self, directory):
        """计算目录哈希值"""
        hash_obj = hashlib.sha256()
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return "empty"
            
        # 收集所有文件
        files = []
        for ext in ['.txt', '.yaml', '.yml']:
            files.extend(sorted(dir_path.glob(f'*{ext}')))
            
        for file in files:
            try:
                with open(file, 'rb') as f:
                    hash_obj.update(f.read())
                hash_obj.update(str(file.name).encode())
            except Exception as e:
                self.logger.error(f"读取文件 {file} 失败: {e}")
                
        return hash_obj.hexdigest()
    
    def check_changes(self):
        """检查文件是否有变化"""
        nodes_dir = self.base_dir.parent / 'nodes'
        hash_file = self.base_dir / '.last_hash'
        
        current_hash = self.calculate_hash(nodes_dir)
        
        # 读取上次哈希
        last_hash = None
        if hash_file.exists():
            with open(hash_file, 'r') as f:
                last_hash = f.read().strip()
                
        # 保存当前哈希
        with open(hash_file, 'w') as f:
            f.write(current_hash)
            
        has_changes = (last_hash is None or last_hash != current_hash)
        
        if has_changes:
            self.logger.info("检测到文件变化")
        else:
            self.logger.info("无文件变化")
            
        return has_changes, current_hash
    
    def merge_files(self):
        """合并文件"""
        self.logger.info("开始合并文件")
        
        nodes_dir = self.base_dir.parent / 'nodes'
        output_dir = self.base_dir / 'output'
        
        # 合并txt文件
        txt_files = sorted(nodes_dir.glob('*.txt'))
        merged_content = []
        
        for txt_file in txt_files:
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        merged_content.append(f"# === {txt_file.name} ===")
                        merged_content.append(content)
                        merged_content.append("")
            except Exception as e:
                self.logger.error(f"读取文件失败 {txt_file}: {e}")
                
        # 写入合并文件
        output_file = output_dir / 'hb.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(merged_content))
            
        self.logger.info(f"已生成合并文件: {output_file}")
        return str(output_file)
    
    def split_by_protocol(self, input_file):
        """按协议拆分"""
        self.logger.info("开始按协议拆分")
        
        protocols = {
            'vless': 'vless://',
            'vmess': 'vmess://',
            'trojan': 'trojan://',
            'ss': 'ss://',
            'ssr': 'ssr://',
            'http': 'http://',
            'https': 'https://',
            'socks5': 'socks5://'
        }
        
        protocol_content = {key: [] for key in protocols.keys()}
        others = []
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    matched = False
                    for proto, prefix in protocols.items():
                        if line.lower().startswith(prefix):
                            protocol_content[proto].append(line)
                            matched = True
                            break
                            
                    if not matched:
                        others.append(line)
                        
            # 写入文件
            output_dir = self.base_dir / 'output'
            for proto, lines in protocol_content.items():
                if lines:
                    output_file = output_dir / f"{proto}.txt"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(lines))
                    self.logger.info(f"生成协议文件: {output_file} ({len(lines)}行)")
                    
            # 其他文件
            if others:
                other_file = output_dir / "other.txt"
                with open(other_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(others))
                self.logger.info(f"生成其他文件: {other_file} ({len(others)}行)")
                
        except Exception as e:
            self.logger.error(f"拆分文件失败: {e}")
            
    def run(self, force=False):
        """运行处理流程"""
        self.logger.info("=" * 50)
        self.logger.info("节点处理系统启动")
        self.logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 50)
        
        # 检查变化
        has_changes, current_hash = self.check_changes()
        
        if not has_changes and not force:
            self.logger.info("无文件变化，跳过处理")
            return False
            
        self.logger.info("开始处理节点文件")
        
        try:
            # 1. 合并文件
            merged_file = self.merge_files()
            
            # 2. 按协议拆分
            self.split_by_protocol(merged_file)
            
            # 3. 生成报告
            self.generate_report()
            
            self.logger.info("✅ 处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"处理失败: {e}")
            return False
            
    def generate_report(self):
        """生成报告"""
        report_file = self.base_dir / 'output' / 'REPORT.md'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"""# 节点处理报告

## 基本信息
- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 系统版本: 1.0.0
- 状态: 完成

## 文件统计
| 文件类型 | 数量 | 说明 |
|---------|------|------|
| 输入文件 | {len(list((self.base_dir.parent / 'nodes').glob('*.txt')))} | 节点文件 |
| 输出文件 | {len(list((self.base_dir / 'output').glob('*.txt')))} | 处理结果 |

## 输出文件列表
""")
            
            output_dir = self.base_dir / 'output'
            for file in sorted(output_dir.glob('*.txt')):
                with open(file, 'r', encoding='utf-8') as infile:
                    line_count = len([l for l in infile if l.strip()])
                f.write(f"- `{file.name}`: {line_count} 行\n")
                
        self.logger.info(f"生成报告: {report_file}")
        

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='节点处理系统')
    parser.add_argument('--force', action='store_true', help='强制运行，忽略变化检查')
    parser.add_argument('--config', default='hb', help='配置目录')
    
    args = parser.parse_args()
    
    processor = NodeProcessor(args.config)
    success = processor.run(force=args.force)
    
    sys.exit(0 if success else 1)
    

if __name__ == "__main__":
    main()
