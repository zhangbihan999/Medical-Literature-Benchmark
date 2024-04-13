# Medical-Literature-Benchmark

## 核心代码：

### app.py

入口函数

### data_crawling.py

从网站上爬取文献，待开发

### data_analyse.py

#### 核心功能：

GPT分析文献+将GPT的分析结果转化为标准的benchmark格式

#### 方法解读：

注：`get_pdf`, `saveIndexToDisk`,  `HybridRetriever`, `get_res`这几个方法不用深究

- `analyse`

==接收jsonl，输出jsonl。==

GPT分析文献，回答`question_list`中的问题

输出结果存储在`analyse_jsonls`目录下

- `analyse_to_benchmark`

==接收jsonl，输出jsonl==

将analyse.jsonl转化为benchmark.jsonl，此时的benchmark不够美观，因此我们进行下面的jsonl转json操作

- `jsonl_to_json`

==接收jsonl，输出json==

将benchmark.jsonl转化为benchmark.json，此时得到的结果即为标准的benchmark

## 文件目录：

### sample_jsons

`data_crawling`爬取到的文章信息会存储在这里

### documents

子目录结构为：documents -> pmid -> pdf + index

- pmid: pubmed上该文献的编号
- pdf: 从网络上下载到的该文献的pdf
- index: RAG切分文献pdf得到的子块

### analyse_jsonls

GPT回答问题后的结果将存储在这里

### benchmark_jsonls

jsonl形式的benchmark存储在这里。根据问题的难易程度划分为`easy`和`challenge`

### benchmark_jsons

json形式的benchmark存储在这里。根据问题的难易程度划分为`easy`和`challenge`

### mock_jsons

手工制作的mock，供接口测试使用

## 当前存在问题

1. 对于“研究国家/地区”这个问题，目前只是简单列了几个国家作为labels，后期实际应用起来的话，估计要加的国家/地区数量是十分庞大的。而且即使我们能够一一穷举，有些文章的标准答案也许会是多个国家/地区的组合，这样一来，我们的labels又该如何应对？
2. 当前我们用来做知识问答的是一整篇文献。但是经北大博士反馈，文献中的References之后的内容一定程度上会误导回答结果的正确性。这就需要我们在进行RAG的切块操作之前，首先直接处理pdf，删掉References之后的内容，目前尚不清楚这一操作如何实现。
3. 目前“给药途径”的labels仅仅是从现有样本集中提取出来的，具体有多少“给药途径”，之后还需要跟博士确认一下

