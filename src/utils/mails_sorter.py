# langchain using ollama/api to sort the fetched emails into different categories

# 思路： 在temp目录下建立一个存储键值对的文件（json），键是分类，值是temp/mails下文件的名称 建立映射关系 
# 分类时按照temp/mails下文件的名称进行分类, 不读取邮件内容 
# 类别： 工作，技术，新闻，其他

import os
import json
from pathlib import Path
from typing import Dict, List
from langchain_core.documents import Document
from langchain_ollama import OllamaLLM
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# 获取当前文件所在目录
current_dir = Path(__file__).parent

# path of temp_dir
tmp_dir = current_dir / ".." / ".." / "temp"
tmp_dir = tmp_dir.resolve()  # 解析相对路径为绝对路径

# 构建mails目录的完整路径
mails_dir = tmp_dir / "mails"

class MailSorter:
    def __init__(self, model_name: str = "deepseek-chat"):
        self.llm = ChatDeepSeek(model=model_name)
        self.categories = ["工作", "技术", "新闻", "其他"]
        self.temp_dir = tmp_dir
        self.mails_dir = mails_dir
        self.mapping_file = self.temp_dir / "category_mapping.json"
        
        # 确保必要的目录存在
        self.temp_dir.mkdir(exist_ok=True)
        self.mails_dir.mkdir(exist_ok=True)
        
    def _load_mapping(self) -> Dict[str, List[str]]:
        """加载现有的分类映射"""
        if self.mapping_file.exists():
            with open(self.mapping_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {category: [] for category in self.categories}
    
    def _save_mapping(self, mapping: Dict[str, List[str]]):
        """保存分类映射到文件"""
        with open(self.mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
            
    def classify_email(self, filename: str) -> str:
        """使用 LLM 对单个邮件进行分类"""
        prompt = PromptTemplate(
            template="""你是一个邮件分类助手。请根据邮件文件名判断其属于哪个类别。

类别必须是以下四个之一：工作、技术、新闻、其他

分类规则：
1. 工作：
   - 所有与招聘、求职相关的内容，包括：
     * 职位发布（比如 software_engineer, developer, 工程师等职位名）
     * 实习机会
     * 公司招聘信息
   - 即使是技术岗位的招聘，也应归类为"工作"
   - 关键词：job, 招聘, 职位, engineer, developer, 工程师, intern, 实习

2. 技术：
   - 技术文章、教程、讨论
   - 开发工具、框架介绍
   - 技术周报、月报
   - 编程语言、AI、开发相关的学习资料
   - 但不包括技术岗位招聘信息
   - 关键词：tutorial, guide, weekly, 教程, 指南, 框架, framework

3. 新闻：时事新闻、重大事件、社会动态等
4. 其他：不属于以上类别的内容

重要提示：如果文件名包含招聘相关信息（比如职位名称），即使同时包含技术内容，也应优先归类为"工作"类。

文件名: {filename}

直接返回类别名称（工作/技术/新闻/其他），不要有任何额外解释。""",
            input_variables=["filename"]
        )
        
        try:
            result = self.llm.invoke(prompt.format(filename=filename))
            # 从 AIMessage 中获取内容
            predicted_category = result.content.strip()
            if predicted_category not in self.categories:
                print(f"警告：文件 '{filename}' 的预测类别 '{predicted_category}' 无效，归类为'其他'")
                return "其他"
            return predicted_category
        except Exception as e:
            print(f"警告：处理文件 '{filename}' 时出错：{str(e)}，归类为'其他'")
            return "其他"
    
    def sort_emails(self):
        """对 temp/mails 目录下的所有邮件进行分类"""
        mapping = self._load_mapping()
        
        # 获取所有邮件文件
        email_files = [f.name for f in self.mails_dir.iterdir() if f.is_file() or f.is_dir()]  # 同时包含文件和目录
        
        if not email_files:
            print("警告：temp/mails 目录下没有找到任何文件")
            return mapping
            
        # 清空现有映射
        mapping = {category: [] for category in self.categories}
        
        # 对每个文件进行分类
        for filename in email_files:
            category = self.classify_email(filename)
            mapping[category].append(filename)
        
        # 保存映射结果
        self._save_mapping(mapping)
        return mapping

def main():
    sorter = MailSorter()
    result = sorter.sort_emails()
    print("\n邮件分类完成！分类结果：")
    
    # 计算总文件数
    total_files = sum(len(files) for files in result.values())
    print(f"\n共处理文件数：{total_files}\n")
    
    for category, files in result.items():
        if files:  # 只显示非空类别
            print(f"\n{category}（{len(files)}个）:")
            for file in files:
                print(f"  - {file}")

if __name__ == "__main__":
    main()




