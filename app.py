import data_analyse
import data_crawling

##############################
##  定义超参，修改目录在这里  ##
##############################

# data_crawling
medicine = './crawl_lists/medicine.json'
medicine_with_entryTerms = "./crawl_lists/medicine_with_entryTerms.jsonl"
medicine_with_search = "./crawl_lists/medicine_with_search.jsonl"
medicine_with_pmid = "./crawl_lists/medicine_with_pmid.jsonl"
medicine_with_content = "./crawl_lists/medicine_with_content.jsonl"
valid_literature = "./crawl_lists/valid_literature.jsonl"

# data_analyse
directory = "./documents/"                                             # 指定下载pdf和进行index操作的父目录路径
source_json = "./sample_jsons/crawl_target_demo_01.json"               # 指定要读取的json
analyse_json = "./analyse_jsonls/analyse_02.jsonl"                       # analyse的结果写入的文件
benchmark_easy_jsonl = "./benchmark_jsonls/benchmark_easy_01.jsonl"          
benchmark_challenge_jsonl = "./benchmark_jsonls/benchmark_challenge_01.jsonl"
benchmark_easy_json = "./benchmark_jsons/benchmark_easy_01.json"  
benchmark_challenge_json = "./benchmark_jsons/benchmark_challenge_01.json"

################################
##        data_crawling       ##
################################    

# 抓取药品别名
# data_crawling.get_entryTerms(medicine, medicine_with_entryTerms)
# 拼接搜索词
# data_crawling.get_search(medicine_with_entryTerms, medicine_with_search)
# 抓取文章id
# data_crawling.get_pmid(medicine_with_search, medicine_with_pmid)
# 抓取文章内容
# data_crawling.get_content(medicine_with_pmid, medicine_with_content)
# gpt判断文章是否有效
# data_crawling.relevance(medicine_with_content, valid_literature)

################################
##        data_analyse        ##
################################

# 调用gpt分析文献
# ata_analyse.analyse(directory, source_json, analyse_json)
# 将文献分析结果转为benchmark格式
# data_analyse.analyse_to_benchmark(analyse_json, benchmark_easy, benchmark_challenge)

# 把benchmark_jsonl转化为benchmark_json
# data_analyse.jsonl_to_json(benchmark_easy_jsonl, benchmark_easy_json)
# data_analyse.jsonl_to_json(benchmark_challenge_jsonl, benchmark_challenge_json)







