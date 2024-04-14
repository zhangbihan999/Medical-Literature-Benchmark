import requests
import re
import os
from bs4 import BeautifulSoup
import pandas as pd
import json
import openai
import logging

# 抓取药品别名
def get_entryTerms(src_file, target_file):
    with open(src_file, "r+", encoding='utf-8') as f:
        json_array = json.load(f)
    for json_obj in json_array:
        common_name_in_English = json_obj["英文通用名"]
        json_obj["entryTerms"] = []
        url1 = "https://www.ncbi.nlm.nih.gov/mesh/?term=" + common_name_in_English
        headers = {
            'Content-Type': 'text/html;charset=utf-8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }         
        response = requests.get(url1, headers=headers)
        ncbi_response = response.text  
        url2 = "https://www.ncbi.nlm.nih.gov/mesh/"
        if "link_uid" in ncbi_response:
            link_uid = ncbi_response.split("link_uid=")[1].split("\">")[0]
            headers = {
                'Content-Type': 'text/html;charset=utf-8',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }            
            response = requests.get(url2 + link_uid, headers=headers)
            ncbi_response = response.text
            print(ncbi_response)
        ncbi_response = ncbi_response.replace("Entry \rTerms", "Entry Terms").replace("Entry \nTerms", "Entry Terms")
        if "No items found" in ncbi_response or "Entry Terms" not in ncbi_response:
            with open(target_file, "a", encoding='utf-8') as f:
                json.dump(json_obj, f, ensure_ascii=False)
                f.write("\n")
            continue
        soup = BeautifulSoup(ncbi_response, 'html.parser')
        entry_terms_list = soup.find('p', text='Entry Terms:').find_next('ul').find_all('li')
        entry_terms = [item.get_text() for item in entry_terms_list]
        print(entry_terms)
        json_obj["entryTerms"] = entry_terms
        with open(target_file, "a", encoding='utf-8') as f:
            json.dump(json_obj, f, ensure_ascii=False)
            f.write("\n")

# 拼接搜索词
def get_search(src_file, target_file):
    json_array = []
    with open(src_file, 'r', encoding='utf-8') as f:
        for line in f:
            json_obj = json.loads(line)
            json_array.append(json_obj)
    init_search_terms = "AND ((\"Adolescent\"[Mesh]) OR (\"Infant\"[Mesh]) OR (\"Infant, Newborn\"[Mesh]) OR (\"Child\"[Mesh]) OR (\"Child, Preschool\"[Mesh]) OR (\"Pediatrics\"[Mesh]) OR (pediatric* [Title/Abstract]) OR (paediatric*[Title/Abstract]) OR (child*[Title/Abstract]) OR (infant*[Title/Abstract]) OR (adolescent*[Title/Abstract]) OR (youth*[Title/Abstract]) OR (junior*[Title/Abstract]) OR (juvenile*[Title/Abstract]) OR (neonat*[Title/Abstract]) OR (newborn*[Title/Abstract]) OR (teenager*[Title/Abstract]) OR (toddler*[Title/Abstract]) OR (boy*[Title/Abstract]) OR (girl*[Title/Abstract]) OR (bab*[Title/Abstract]) OR (preschool*[Title/Abstract]) OR (pre-school*[Title/Abstract])) AND ((\"Study Characteristics\" [Publication Type]) OR (\"Guideline\" [Publication Type]) OR (\"clinical trial\"[Title/Abstract]) OR (\"randomized trial\"[Title/Abstract]) OR (\"cohort study\"[Title/Abstract]) OR (\"single arm study\"[Title/Abstract]) OR (\"single arm trial\"[Title/Abstract]) OR (\"systematic review\"[Title/Abstract]) OR (\"n-of-1 trial\"[Title/Abstract]) OR (\"case report\"[Title/Abstract]) OR (\"case-control study\"[Title/Abstract]) OR (\"observational study\"[Title/Abstract]) OR (\"controlled study\"[Title/Abstract]) OR (\"controlled trial\"[Title/Abstract]) OR (\"case-series\"[Title/Abstract]) OR (\"prospective study\"[Title/Abstract]) OR (\"retrospective study\"[Title/Abstract]))";

    for json_obj in json_array:
        print(json_obj)
        common_name_in_English = json_obj["英文通用名"]
        entry_terms = json_obj["entryTerms"]
        entry_terms_str = "("
        if entry_terms is not None and len(entry_terms) > 0:
            for sub_term in entry_terms:
                if " " in sub_term:
                    sub_term = "\"" + sub_term + "\""
                entry_terms_str = entry_terms_str + sub_term + ") OR ("
            entry_terms_str = entry_terms_str[:-5]
        common_name_in_English = "\"" + common_name_in_English + "\"" if " " in common_name_in_English else common_name_in_English
        common_name_in_English = "(" + common_name_in_English + ")"
        if len(entry_terms_str) > 0:
            search = common_name_in_English + " OR" + entry_terms_str
        search = "(" + search + ")" + init_search_terms
        json_obj["search"] = search
        with open(target_file, "a", encoding='utf-8') as f:
            json.dump(json_obj, f, ensure_ascii=False)
            f.write("\n")

# 抓取文章id
def get_pmid(src_file, target_file):
    url1 = "https://pubmed.ncbi.nlm.nih.gov/?"
    json_array = []
    finish_ids = []
    with open(target_file, 'r', encoding='utf-8') as f:
        for line in f:
            json_obj = json.loads(line)
            json_array.append(json_obj)
            finish_ids.append(line["药品序号"])
    with open(src_file, 'r', encoding='utf-8') as f:
        for line in f:
            json_obj = json.loads(line)
            json_array.append(json_obj)
    for json_obj in json_array:
        search = json_obj["search"]
        headers = {
            'Content-Type': 'text/html;charset=utf-8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }   
        response = requests.get(url1 + "term=" + search, headers=headers)
        text_search_list = response.text
        if "log_resultcount" not in text_search_list:
            if "meta name=\"uid\" content=\"" in text_search_list:
                soup = BeautifulSoup(text_search_list, 'html.parser')
                uid = soup.find('meta', {'name': 'uid'})['content']
                json_obj["data-chunk-ids"] = {uid}
                with open(target_file, 'a', encoding='utf-8') as f:
                    json.dump(json_obj, f, ensure_ascii=False)
                    f.write("\n")
        else:
            soup = BeautifulSoup(text_search_list, 'html.parser')
            total = int(soup.find('meta', {'name': 'log_resultcount'})['content'])
            if total == 0:
                with open(target_file, 'r', encoding='utf-8') as f:
                    json.dump(json_obj, f, ensure_ascii=False)
                    f.write("\n")  
            else:
                uid_list_str = soup.find(attrs={"data-chunk-ids": True}).get("data-chunk-ids")
                uid_list = uid_list_str.split(",")
                data_ids = set(uid_list)
                if total > 10:
                    total_page = total / 10 + 1
                    for page in range(2, int(total_page) + 1):
                        response = requests.get(url1 + "page=" + str(page) + "&terms=" + search, headers=headers)
                        text_search_list = response.text
                        if "data-chunk-ids" not in text_search_list and page == total_page: continue
                        retry = 0
                        while "data-chunk-ids" not in text_search_list:
                            retry += 1
                            response = requests.get(url1 + "page=" + str(page) + "&terms=" + search, headers=headers)
                            text_search_list = response.text
                            if retry >= 3:
                                text_search_list = text_search_list + "data-chunk-ids=\" \""
                                break
                        if page > 200: break
                        uid_list1_str = soup.find(attrs={"data-chunk-ids": True}).get("data-chunk-ids")
                        uid_list1 = uid_list1_str.split(",")
                        data_ids.update(uid_list1)
                        print("total: {}, page: {}".format(total, page) )
                json_obj["data-chunk-ids"] = list(data_ids)
                with open(target_file, 'a', encoding='utf-8') as f:
                    json.dump(json_obj, f, ensure_ascii=False)
                    f.write("\n") 

# 抓取文章内容
def get_content(src_file, target_file):
    url1 = "https://pubmed.ncbi.nlm.nih.gov/"
    json_array = []
    finish_ids = []
    with open(target_file, 'r+', encoding='utf-8') as f:
        json_array = []
        for line in f:
            json_obj = json.loads(line)
            json_array.append(json_obj)
            finish_ids.append(json_obj["药品序号"])
    with open(src_file, 'r', encoding='utf-8') as f:
        for line in f:
            json_obj = json.loads(line)
            json_array.append(json_obj)
    for json_obj in json_array:
        ids = json_obj["data-chunk-ids"]
        if ids is not None:
            texts = []
            for i,id in enumerate(ids):
                print("total: {}, page: {}".format(len(ids), i))
                text_obj = {}
                if len(id) == 0: continue
                try:
                    headers = {
                        'Content-Type': 'text/html;charset=utf-8',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }   
                    response = requests.get(url1 + id, headers=headers)
                    body = response.text
                    soup = BeautifulSoup(body, 'html.parser')
                    title = soup.title.string
                    text_obj["title"] = title
                    text_obj["id"] = id

                    # 抓取发表年份
                    year_elements = soup.select(".article-source .cit")
                    if year_elements:
                        child_text = year_elements[0].text.split(";")[0].strip()
                        text_obj["year"] = child_text

                    # 抓取abstract
                    eng_abstract = soup.find(id="eng-abstract")
                    if eng_abstract is not None:
                        text = eng_abstract.text.replace("&amp;", " ").replace("<[^>]*>", "").replace("\n"," ")
                        text_obj["abstract"] = re.sub(r'\s+', ' ',text).strip()
                    texts.append(text_obj)
                except Exception as e:
                    print("Exception: ", e)
            json_obj["texts"] = texts
            with open(target_file, 'a', encoding='utf-8') as f:
                json.dump(json_obj, f, ensure_ascii=False)
                f.write("\n") 

# GPT判断是否相关
def relevance(src_file, target_file):
    json_array = []
    finish_ids = []
    with open(target_file, 'r+', encoding='utf-8') as f:
        json_array = []
        for line in f:
            json_obj = json.loads(line)
            json_array.append(json_obj)
            finish_ids.append(json_obj["药品序号"])
    with open(src_file, 'r', encoding='utf-8') as f:
        for line in f:
            json_obj = json.loads(line)
            json_array.append(json_obj)
    for data in json_array:
        texts = data["texts"]
        new_texts = []
        for i, text in enumerate(texts):
            print("total: ", len(texts), " page: ", i)
            if "title" not in text or len(text["title"]) == 0: continue
            try:
                content = get_chat_completion(
                    f"### I want you to work as a pharmaceutical researcher.\n"
                    f"I will give you the title and abstract of a paper about a certain drug, "
                    f"you are responsible for judging whether it's an efficient study of this drug for pediatric patients or not.\n"
                    f"Systematic review and meta-analysis, systematic review, n-of-1 trial, RCT, "
                    f"non-randomized controlled cohort/follow-up study, case-series, case-control study, "
                    f"historically controlled study, single-arm study, literature review, guideline are all OK, too.\n"
                    f"You are requested to think as carefully as possible. Your answer should be in this template:\n"
                    f"'A concise and correct analysis with less than 200 tokens. Then based on this, you should say: "
                    f"(if it's a research paper) `Thus, it does/doesn't directly address the efficiency of this drug "
                    f"for pediatric patients in this context.` (if it's a case report/series) `Thus, it's an efficient case "
                    f"report/series of this drug for pediatric patients in this context.`\n"
                    f"Then end with a JSON: {{'Judgement': 'Yes/No'}}'\n"
                    f"###\nHere is the given information in this order:\n"
                    f"name of drug: `{data['英文通用名']}`\n"
                    f"Title: `{text['title']}`\n"
                    f"Abstract: `{text['abstract']}`"
                )                
                if "Yes" in content:
                    new_texts.append(text)
            except Exception as e:
                print("Exception: ", e)
        data["texts"] = new_texts
        with open(target_file, 'a', encoding='utf-8') as f:
            json.dump(json_obj, f, ensure_ascii=False)
            f.write("\n")

class OpenAILogger:
    def log(self, message):
        print(message)

def get_openai_client():
    openai_logger = OpenAILogger()
    openai.api_key = "your api key"
    openai.api_host = "your api host"
    return openai

def get_chat_completion(text):
    openai_client = get_openai_client()

    chat_completion = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": text
            }
        ],
        "response_format": "json"
    }
    response = openai_client.completions.create(
        model="gpt-3.5-turbo", 
        prompt=text
    )
    completion_text = response['choices'][0]['message']['content']
    return completion_text

