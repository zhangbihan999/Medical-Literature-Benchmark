import data_analyse

# 定义超参，修改父目录位置在这里
directory = "./documents/"                                             # 指定下载pdf和进行index操作的父目录路径
source_json = "./sample_jsons/sample_from_list6+_01.json"              # 指定要读取的json
analyse_json = "./analyse_jsonls/analyse_02.jsonl"                       # analyse的结果写入的文件
benchmark_easy_jsonl = "./benchmark_jsonls/benchmark_easy_01.jsonl"          
benchmark_challenge_jsonl = "./benchmark_jsonls/benchmark_challenge_01.jsonl"
benchmark_easy_json = "./benchmark_jsons/benchmark_easy_01.json"  
benchmark_challenge_json = "./benchmark_jsons/benchmark_challenge_01.json"

# 调用gpt分析文献
# ata_analyse.analyse(directory, source_json, analyse_json)
# 将文献分析结果转为benchmark格式
# data_analyse.analyse_to_benchmark(analyse_json, benchmark_easy, benchmark_challenge)

# 把benchmark_jsonl转化为benchmark_json
data_analyse.jsonl_to_json(benchmark_easy_jsonl, benchmark_easy_json)
data_analyse.jsonl_to_json(benchmark_challenge_jsonl, benchmark_challenge_json)







