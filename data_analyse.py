import os
import json
import jsonlines
import requests
from playwright.async_api import async_playwright
import pandas as pd
import asyncio
from llama_index.core import ServiceContext, SimpleDirectoryReader, StorageContext, VectorStoreIndex, get_response_synthesizer, load_index_from_storage, Response
from llama_index.core.evaluation import RelevancyEvaluator
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SentenceTransformerRerank

# 从环境变量中获取API key
os.environ['OPENAI_API_KEY'] = 'your api key'

# 0-4 为easy; 5-12为challenge
questions_list = [
 # 0 样本数量 scorer number
 "What is the sample size of this study? Or how many children under 18 years old were involved in this study, only return number? eg1: 100 eg2: 24 eg3: 31 ",
 # 1 研究国家/地区 question answer labels(list)
 "Which countries or regions was the study conducted in? (only return the name of country or region) eg1: China eg2: Germany, Turkey, Belgium, and the United States",
 # 2 是否对照  question answer labels(Yes/No)
 "Were the sample patients divided into different groups with different treatment? If yes,  Only return Yes or No.",
 # 3 研究类型 question answer labels(list)
 "What is the study type of this study? Please choose one of the following choices: dose optimization study, formulation optimization research, systematic review and meta analysis, systematic review, n-of-1 trial, RCT, non-randomized controlled cohort/follow-up study, case-series, case-control study, historically controlled study, single arm study, literature review, guideline, or others?",
 # 4 给药途径 question answer labels
 "What is the route of administration of latamoxef in this research? Please answer like: Oral, intravenous. If actually there is no relevant content in given materials, you are limited to answer 'Not mentioned', but be carefully to do this.",
 # 5 研究疾病 question answer text
 "What is the type of disease studied in this research? eg: Chronic Myeloid Leukemia (CML)",
 # 6 对照组提取 question answer text
 "What was the treatment for patients in control group? Please tell the generic name, route of administration, dosage and frequency.",
 # 7 对照组药品 question answer text
 "What was the studied medicine's name in control group? Only return the generic name. eg: Glucurolactone",
 # 8 干预组提取 question answer text
 "What was the treatment for patients in experimental (or intervention) group? Please tell the generic name, route of administration, dosage and frequency.",
 # 9 干预组药品 question answer text
 "What was the studied medicine's name in experimental (or intervention) group? Only return the generic name.    eg: Ganciclovir",
 # 10 研究人群年龄 scorer number
 "What is the age range of patients studied in this research?    If there is a specific numeric range, please answer like: minimum value - maximum value (e.g., 12-15, or 10 months-6);    If there's no specific numeric range, only categories for the age groups of the study population,please answer like: 'Newborn' or 'Infant' or 'Child' or 'Adolescent';    If there are 2 or more, separate them with a semicolon, please answer like: newborn; infant    If actually there is no relevant content in given materials, you are able to answer 'Not mentioned', but be carefully to do this.",
 # 11 研究结论 common sense text
 "What is the conclusion of this research? Make your answer concise.",
 # 12 outcome common sense text
 "What is measured for results in this study? Please list all of the outcomes. Separate each term with ';'. eg1: Duration of postoperative analgesia(; Number of patients requiring rescue analgesics eg2: Lesion size; Side effects related to treatment eg3: pCO2; pO2; Base excess; Lactate; Umbilical vein pH  eg4: CSF cell count; CSF glucose concentration;PRP determination; Duration of illness prior to admission; Prolonged fever;",
]

# download pdf
async def get_pdf(directory, proxy, pmid):
    async with async_playwright() as playwright:
        # 准备工作
        if proxy:
            browser_ui = await playwright.firefox.launch(headless=False, proxy={"server": proxy})
        else:
            browser_ui = await playwright.firefox.launch(headless=False)
        page = await browser_ui.new_page()
        await page.goto(f"https://www.sci-hub.yt/")
        ua =await page.evaluate("navigator.userAgent")
        cookie = {}
        for k in await page.context.cookies():
            if "sci-hub.yt" in k['domain']:
                cookie[k["name"]] = k["value"]
        await page.close()
        proxies = {
            "http": proxy,
            "https": proxy
        }
    # 下载文章pdf
    ret=requests.get("https://pubmed.ncbi.nlm.nih.gov/"+pmid,proxies=proxies).text
    # 判断是否有doi号码
    if "citation-doi" in ret:
        # 提取doi号码
        doi=ret.split("citation-doi")[1].split("<")[0]
        doi=doi.split("doi")[1].strip()
        if doi[-1]==".":
            doi=doi[:-1]
        if doi[0]==":":
            doi=doi[1:]
        doi=doi.strip()
        # 判断pdf文件是否存在
        view_url=f"https://www.sci-hub.yt/{doi}"
        pdf_page = requests.get(view_url,cookies=cookie,headers={"User-Agent":ua}, proxies=proxies)
        if os.path.exists(directory + f"{pmid}"):   # 这级目录存在就说明已经下载了其pdf，直接return退出
            print(f"已下载{pmid}，不用重复下载")
            return
        # 如果pdf存在，则下载pdf
        if pdf_page.status_code == 200:
            if "onclick=\"location" in pdf_page.text:
                url=pdf_page.text.split("onclick=\"location")[1].split(">")[0]
                url=url.replace(".href='","").replace("'\"","").replace("\\","")

                pdf=requests.get(url,cookies=cookie,headers={"User-Agent":ua}, proxies=proxies)
                if pdf.status_code!=200:
                    print("url不存在!",pmid,doi)
                    print()
                else:
                    if not os.path.exists(directory + f"{pmid}"):              # 如果不存在这一级目录就创建它
                        os.makedirs(directory + f"{pmid}")
                        print(f"目录{pmid}创建成功")
                        print()
                    with open(directory + f"{pmid}/{pmid}.pdf", "wb+") as f:
                        f.write(pdf.content)
                    print("下载成功",pmid,doi)
                    print()
            else:
                print("没有找到pdf文件",pmid,doi,view_url)
                print()
        else:
            print("sci-hub没有检测到资源,pdf下载失败",doi)
            print()

# 定义index的获取和存储方式
def saveIndexToDisk(input_files, persist_dir):                              # 这里的input_files需要是一个列表
    documents = SimpleDirectoryReader(input_files=input_files).load_data()                 # 读取文件内容
    service_context = ServiceContext.from_defaults(chunk_size=400, chunk_overlap=50)       # 定义chunk方法
    index = VectorStoreIndex.from_documents(documents, service_context=service_context)    # 按照定义的方法进行切分并标定index
    index.storage_context.persist(persist_dir=persist_dir)                                 # 将得到的index存储在指定地址
  
# 构建HybridRetriever类
class HybridRetriever(BaseRetriever):
    def __init__(self, vector_retriever, bm25_retriever):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        super().__init__()

    def _retrieve(self, query, **kwargs):
        bm25_nodes = self.bm25_retriever.retrieve(query, **kwargs)
        vector_nodes = self.vector_retriever.retrieve(query, **kwargs)

        # combine the two lists of nodes
        all_nodes = []
        node_ids = set()
        for n in bm25_nodes + vector_nodes:
            if n.node.node_id not in node_ids:
                all_nodes.append(n)
                node_ids.add(n.node.node_id)
        return all_nodes

# 获取回答和node
def get_res(directory, question, doi):
    storage_context = StorageContext.from_defaults(persist_dir=directory + f"/{doi}/index")    # 获取本文献doi目录下的index
    index = load_index_from_storage(storage_context)
    # get a retriever from index
    vector_retriever = index.as_retriever(similarity_top_k=10)  # 这个retriever是在向量层面，或者说语义层面上，去计算相似度的
    bm25_retriever = BM25Retriever.from_defaults(index=index, similarity_top_k=10)  # 这个retriever是在文本表面特征层面计算相似度的
    retriever = HybridRetriever(vector_retriever, bm25_retriever)  # 我们构建一个混合了上述两个retriever的retriever，理论上能达到更好的效果
    # 获取响应生成器
    response_synthesizer = get_response_synthesizer(  # A Response Synthesizer is what generates a response from an LLM, using a user query and a given set of text chunks. The output of a response synthesizer is a Response object.
        response_mode='tree_summarize',  # compact，simple_summarize，tree_summarize，这是三种文本摘要方法，其中tree_summarize是精度最高的方法，适用于对文本进行深度处理，compact和simple_summarize都对细节不太敏感
        streaming=False  # streaming参数指定是否使用流式处理来获取响应。若为True，表示使用，即在获取响应时逐步返回结果；若为False，即不使用，在获取完整的响应后u一次性返回结果
    )

     # 用构建的retriever进行召回操作
    retrieve_nodes = retriever._retrieve(question)
    print("--------before rerank-----------")
    for node in retrieve_nodes:
        print(node.node)
    print("--------------------------------")
    # 用reranker重新对node进行排名
    reranker = SentenceTransformerRerank(top_n=5, model="BAAI/bge-reranker-base")
    retrieve_nodes = reranker.postprocess_nodes(retrieve_nodes, query_str=question)
    print("--------after rerank------------")
    for node in retrieve_nodes:
        print(node.node)
    print("---------------------------------")
    # 获取响应
    response = response_synthesizer.synthesize(query=question, nodes=retrieve_nodes)
    return response, retrieve_nodes

# 分析下载到了pdf的文献(因为没有pdf的话无法做RAG)
def analyse(directory, source_json, analyse_jsonl):
    finishedIds = []
    with open(analyse_jsonl, "r+", encoding='utf-8') as f:
        json_array = []
        for line in f:
            json_obj = json.loads(line)
            json_array.append(json_obj)
            finishedIds.append(line["药品序号"])
    with open(source_json, "r+", encoding='utf-8') as source_file:
        json_array = json.load(source_file)
    for data in json_array:
        new_texts = []
        if data["药品序号"] in finishedIds: continue
        for text in data["texts"]:
            id = text["id"]
            # 初始化text
            text["pdf"] = ""

            text["easy"] = {}
            text["easy"]["样本数量"] = ""
            text["easy"]["研究国家/地区"] = ""
            text["easy"]["是否对照"] = ""
            text["easy"]["研究类型"] = ""
            text["easy"]["给药途径"] = ""

            text["challenge"] = {}
            text["challenge"]["研究疾病"] = ""           
            text["challenge"]["对照组提取"] = ""
            text["challenge"]["对照组药品"] = ""
            text["challenge"]["干预组提取"] = ""
            text["challenge"]["干预组药品"] = ""
            text["challenge"]["研究人群年龄"] = ""
            text["challenge"]["研究结论"] = ""
            text["challenge"]["outcome"] = ""

            # 下载pdf
            asyncio.run(get_pdf(directory, "http://127.0.0.1:10086", id))
            if not os.path.exists(directory + "{}".format(id)): 
                text["pdf"] = "NA"
                continue    # 如果经过get_pdf方法后还没有本级目录，说明这篇文章的pdf没下载下来，一般是因为其pdf不存在
            if not os.path.exists(directory + "{}/index".format(id)):           # if not，避免重复index
                saveIndexToDisk([directory + "{}/{}.pdf".format(id, id)], directory + "{}/index".format(id))   # 将每一篇文章的index存储到其目录下
   
            # 逐个回答问题并对其编号，根据编号决定作为哪一个key写入jsonl
            for number, question in enumerate(questions_list):      
                print("Current question: ", number)  
                # 更新data的texts里的每一个text
                if number == 0: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["easy"]["样本数量"] = response.response 
                elif number == 1: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["easy"]["研究国家/地区"] = response.response 
                elif number == 2: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["easy"]["是否对照"] = response.response 
                elif number == 3: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["easy"]["研究类型"] = response.response 
                elif number == 4: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["easy"]["给药途径"] = response.response 
                elif number == 5: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["challenge"]["研究疾病"] = response.response 
                elif number == 6: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["challenge"]["对照组提取"] = response.response 
                elif number == 7: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["challenge"]["对照组药品"] = response.response
                elif number == 8: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["challenge"]["干预组提取"] = response.response
                elif number == 9: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["challenge"]["干预组药品"] = response.response
                elif number == 10: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["challenge"]["研究人群年龄"] = response.response
                elif number == 11: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["challenge"]["研究结论"] = response.response   
                elif number == 12: 
                    response, retrieve_nodes = get_res(directory, question, id)
                    text["challenge"]["outcome"] = response.response                                         
                # 将每个问题的top_5 nodes也添加到jsonl里面,作为paragraphs
                for num, node_with_score in enumerate(retrieve_nodes):
                    text["question_{}_node_{}".format(number,num)] = node_with_score.text

            new_texts.append(text)
            
        data["texts"] = new_texts
        # 将data写入analyse_jsonl文件
        with open(analyse_jsonl, 'a', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            f.write("\n")

# analyse.jsonl -> benchmark.jsonl
def analyse_to_benchmark(analyse_jsonl, benchmark_easy, benchmark_challenge):
    with open(analyse_jsonl, "r+", encoding='utf-8') as f:
        json_array = []
        for line in f:
            json_obj = json.loads(line)
            json_array.append(json_obj)
    for data in json_array:
        for text in data["texts"]:
            for num in range(13):
                unit = {}
                unit["question"] = questions_list[num]
                unit["paragraphs"] = []
                for i in range(5):
                    unit["paragraphs"].append(text["question_{}_node_{}".format(num, i)])

                unit["properties"] = {}
                unit["properties"]["doi"] = text["doi"]
                unit["properties"]["url"] = "https://pubmed.ncbi.nlm.nih.gov/{}/".format(text["id"])
                # 根据问题设置subject
                if num == 0 or num == 10: unit["properties"]["subject"] = "scorer"
                elif num == 1 or num == 2 or num == 2 or num == 3 or num == 4 or num == 5 or num == 6 or num == 7 or num == 8 or num == 9 : unit["properties"]["subject"] = "question answer"
                elif num == 11 or num == 12: unit["properties"]["subject"] = "common sense"

                # 根据问题配对answer
                if num == 0: unit["answer"] = text["easy"]["样本数量"]
                elif num == 1: unit["answer"] = text["easy"]["研究国家/地区"]
                elif num == 2: unit["answer"] = text["easy"]["是否对照"]
                elif num == 3: unit["answer"] = text["easy"]["研究类型"]
                elif num == 4: unit["answer"] = text["easy"]["给药途径"]
                elif num == 5: unit["answer"] = text["challenge"]["研究疾病"]
                elif num == 6: unit["answer"] = text["challenge"]["对照组提取"]
                elif num == 7: unit["answer"] = text["challenge"]["对照组药品"]
                elif num == 8: unit["answer"] = text["challenge"]["干预组提取"]
                elif num == 9: unit["answer"] = text["challenge"]["干预组药品"]
                elif num == 10: unit["answer"] = text["challenge"]["研究人群年龄"]
                elif num == 11: unit["answer"] = text["challenge"]["研究结论"]
                elif num == 12: unit["answer"] = text["challenge"]["outcome"]

                # 根据问题配对answer_format 中的type
                unit["answer_format"] = {}
                if num == 0 or num == 10: unit["answer_format"]["type"] = "number"
                elif num == 1 or num == 2 or num == 3 or num == 4: unit["answer_format"]["type"] = "labels"
                elif num == 5 or num == 6 or num == 7 or num == 8 or num == 9 or num == 11 or num == 12: unit["answer_format"]["type"] = "text"

                # 根据问题配对answer format 中的labels
                if num == 1: unit["answer_format"]["labels"] = ["China", "USA", "UK", "Vietnam", "Nepal", "Japan", "France", "Canada"]    
                elif num == 2: unit["answer_format"]["labels"] = ["Yes", "No"]
                elif num == 3: unit["answer_format"]["labels"] = ["Dose optimization study", "Formulation optimization research", "Systematic review and meta analysis, systematic review", "n-of-1 trial", "RCT", "Non-randomized controlled cohort/follow-up study", "Case-series", "Case-control study", "Historically controlled study", "Single arm study", "Literature review", "Guideline", "Others"]
                elif num == 4: unit["answer_format"]["labels"] = ["Intravenous", "Oral", "Intramuscular", "Inhaled", "Topical"]

                # 根据问题配对full_answer
                if num == 0: unit["full_answer"] = "The number of people involved in the study: {}".format(unit["answer"])
                elif num == 1: unit["full_answer"] = "The study was conducted in {}".format(unit["answer"])
                elif num == 2: 
                    if unit["answer"] == "Yes":
                        unit["full_answer"] = "{}, the sample patients were divided into different groups with different treatment.".format(unit["answer"])
                    elif unit["answer"] == "No":
                        unit["full_answer"] = "{}, the sample patients were not divided into different groups with different treatment.".format(unit["answer"])
                elif num == 3:
                    unit["full_answer"] = "The study type of this study is {}.".format(unit["answer"])
                elif num == 4:
                    unit["full_answer"] = "The route of administration of {} in this research is {}.".format(data["英文通用名"], unit["answer"])

                # 根据问题分类写入不同的文件
                if num < 5:
                    with open(benchmark_easy, 'a', encoding='utf-8') as f:
                        json.dump(unit, f, ensure_ascii=False)
                        f.write("\n")
                else:
                    with open(benchmark_challenge, 'a', encoding='utf-8') as f:
                        json.dump(unit, f, ensure_ascii=False)
                        f.write("\n")
            
# benchmark.jsonl -> benchmark.json
def jsonl_to_json(benchmark_jsonl, benchmark_json):
    json_array = []
    with open(benchmark_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            json_obj = json.loads(line)
            json_array.append(json_obj)

    with open(benchmark_json, 'w', encoding='utf-8') as f:
        json.dump(json_array, f, indent=4, ensure_ascii=False)












