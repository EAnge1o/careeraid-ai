import sqlite3
import csv
from datetime import datetime

# 连接到SQLite数据库
conn = sqlite3.connect('careeraid.db')
cursor = conn.cursor()

# 获取当前时间
now = datetime.now().isoformat()

# 从CSV文件导入数据
with open('data/jobs_sample.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    
    imported = 0
    for row in rows:
        title = (row.get('title') or row.get('岗位名称') or '').strip()
        if not title:
            continue
            
        industry = (row.get('industry') or row.get('行业') or '').strip() or None
        salary = (row.get('salary') or row.get('薪资') or '').strip() or None
        requirements_text = (row.get('requirements_text') or row.get('岗位要求') or row.get('要求') or '').strip() or None
        
        # 检查是否已存在
        cursor.execute('SELECT id FROM jobs WHERE title = ?', (title,))
        existing = cursor.fetchone()
        
        if existing:
            # 更新
            cursor.execute('''
                UPDATE jobs SET industry=?, salary=?, requirements_text=?, updated_at=?
                WHERE title=?
            ''', (industry, salary, requirements_text, now, title))
        else:
            # 插入（包含所有字段）
            cursor.execute('''
                INSERT INTO jobs (title, industry, salary, requirements_text, job_profile_json, 
                                work_address, company_name, company_scale, company_nature, 
                                job_code, job_desc, company_intro, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, industry, salary, requirements_text, None, None, None, None, None, None, None, None, now, now))
        
        imported += 1

conn.commit()
print(f'导入完成：{imported} 条岗位数据')

# 验证导入结果
cursor.execute('SELECT COUNT(*) FROM jobs')
count = cursor.fetchone()[0]
print(f'数据库中现有岗位数：{count}')

cursor.execute('SELECT title, industry, salary FROM jobs')
for row in cursor.fetchall():
    print(f'  - {row[0]} ({row[1]} - {row[2]})')

conn.close()
