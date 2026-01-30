"""
Author: Joon Sung Park (joonspk@stanford.edu)
Modified for DeepSeek compatibility with robust JSON parsing and error recovery.
"""
import json
import random
import openai
import time 
import re 

from utils import *

# 强制指向 DeepSeek 服务器
openai.api_base = "https://api.deepseek.com" 
openai.api_key = "openai_api_key"

def temp_sleep(seconds=0.1):
    time.sleep(seconds)

def ChatGPT_single_request(prompt): 
    temp_sleep()
    try:
        completion = openai.ChatCompletion.create(
            model="deepseek-chat", 
            messages=[{"role": "user", "content": prompt}]
        )
        return completion["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Single Request Error: {e}")
        return "error"

# ============================================================================
# #####################[SECTION 1: CHATGPT-3 STRUCTURE] ######################
# ============================================================================

def GPT4_request(prompt): 
    temp_sleep()
    try: 
        completion = openai.ChatCompletion.create(
        model="deepseek-chat", 
        messages=[{"role": "user", "content": prompt}]
        )
        return completion["choices"][0]["message"]["content"]
    except Exception as e: 
        print (f"ChatGPT ERROR: {e}")
        return "ChatGPT ERROR"

def ChatGPT_request(prompt): 
  # 确保这里使用了最新的配置
  import openai
  from utils import openai_api_key
  
  openai.api_key = openai_api_key
  openai.api_base = "https://api.deepseek.com" # 必须有这一行！

  try: 
    response = openai.ChatCompletion.create(
      model="deepseek-chat", # 必须改为 deepseek-chat
      messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
  except Exception as e: 
    print(f"ChatGPT ERROR: {e}")
    return None

def GPT4_safe_generate_response(prompt, 
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False): 
    prompt = '"""\n' + prompt + '\n"""\n'
    prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
    prompt += "Example output json:\n"
    prompt += '{"output": "' + str(example_output) + '"}'

    if verbose: 
        print ("CHAT GPT PROMPT")

    for i in range(repeat): 
        try: 
            curr_gpt_response = GPT4_request(prompt).strip()
            
            # --- 核心修复：自动补全缺失的右大括号 ---
            if curr_gpt_response.count('{') > curr_gpt_response.count('}'):
                curr_gpt_response += "}"
            
            # 使用正则提取 JSON 内容
            json_match = re.search(r'\{.*\}', curr_gpt_response, re.DOTALL)
            if json_match:
                curr_gpt_response = json_match.group()
            
            parsed_json = json.loads(curr_gpt_response)
            output_content = parsed_json["output"]
            
            if func_validate(output_content, prompt=prompt): 
                return func_clean_up(output_content, prompt=prompt)
        except Exception as e: 
            if verbose: print(f"Attempt {i} failed: {e}")
            pass
    return False

def ChatGPT_safe_generate_response(prompt, 
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False): 
    prompt = '"""\n' + prompt + '\n"""\n'
    prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
    prompt += "Example output json:\n"
    prompt += '{"output": "' + str(example_output) + '"}'

    if verbose: 
        print ("CHAT GPT PROMPT")

    for i in range(repeat): 
        try: 
            curr_gpt_response = ChatGPT_request(prompt).strip()
            
            # --- 核心修复：自动补全缺失的右大括号 ---
            if curr_gpt_response.count('{') > curr_gpt_response.count('}'):
                curr_gpt_response += "}"

            json_match = re.search(r'\{.*\}', curr_gpt_response, re.DOTALL)
            if json_match:
                curr_gpt_response = json_match.group()

            parsed_json = json.loads(curr_gpt_response)
            output_content = parsed_json["output"]
            
            if func_validate(output_content, prompt=prompt): 
                return func_clean_up(output_content, prompt=prompt)
        except Exception as e: 
            if verbose: print(f"Attempt {i} failed: {e}")
            pass
    return False

# ============================================================================
# ###################[SECTION 2: ORIGINAL GPT-3 STRUCTURE] ###################
# ============================================================================

def GPT_request(prompt, gpt_parameter): 
    temp_sleep()
    model = "deepseek-chat" 
    try: 
        response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=gpt_parameter["temperature"],
                max_tokens=gpt_parameter["max_tokens"],
                top_p=gpt_parameter["top_p"],
                frequency_penalty=gpt_parameter["frequency_penalty"],
                presence_penalty=gpt_parameter["presence_penalty"],
                stop=gpt_parameter["stop"],)
        return response.choices[0].message.content
    except Exception as e: 
        print (f"DeepSeek API 报错: {e}")
        return "TOKEN LIMIT EXCEEDED"

def generate_prompt(curr_input, prompt_lib_file): 
    if type(curr_input) == type("string"): 
        curr_input = [curr_input]
    curr_input = [str(i) for i in curr_input]

    with open(prompt_lib_file, "r", encoding='utf-8') as f:
        prompt = f.read()
    
    for count, i in enumerate(curr_input):   
        prompt = prompt.replace(f"!<INPUT {count}>!", i)
    if "<commentblockmarker>###</commentblockmarker>" in prompt: 
        prompt = prompt.split("<commentblockmarker>###</commentblockmarker>")[1]
    return prompt.strip()

def safe_generate_response(prompt, 
                           gpt_parameter,
                           repeat=5,
                           fail_safe_response="error",
                           func_validate=None,
                           func_clean_up=None,
                           verbose=False): 
    for i in range(repeat): 
        curr_gpt_response = GPT_request(prompt, gpt_parameter)
        try:
            if func_validate(curr_gpt_response, prompt=prompt): 
                return func_clean_up(curr_gpt_response, prompt=prompt)
        except Exception as e:
            if verbose: print(f"Safe Generate Attempt {i} Error: {e}")
            pass
        if verbose: 
            print ("---- repeat count: ", i, curr_gpt_response)
    return fail_safe_response

# --- 本地向量部分保持不变 ---
from sentence_transformers import SentenceTransformer
embed_model = SentenceTransformer('paraphrase-MiniLM-L6-v2') 

def get_embedding(text, model=""):
    text = text.replace("\n", " ")
    if not text: text = "this is blank"
    return embed_model.encode(text).tolist()