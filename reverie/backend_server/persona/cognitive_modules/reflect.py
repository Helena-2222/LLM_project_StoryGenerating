"""
Author: Joon Sung Park (joonspk@stanford.edu)
Modified for: Dramatic Narrative Generation
"""
import sys
sys.path.append('../../')

import datetime
import random

from numpy import dot
from numpy.linalg import norm

from global_methods import *
from persona.prompt_template.run_gpt_prompt import *
from persona.prompt_template.gpt_structure import *
from persona.cognitive_modules.retrieve import *

def generate_focal_points(persona, n=5): # 改装点：由3增加到5，扩大思考广度
  if debug: print ("GNS FUNCTION: <generate_focal_points>")
  
  nodes = [[i.last_accessed, i]
            for i in persona.a_mem.seq_event + persona.a_mem.seq_thought
            if "idle" not in i.embedding_key]

  nodes = sorted(nodes, key=lambda x: x[0])
  nodes = [i for created, i in nodes]

  statements = ""
  for node in nodes[-1*persona.scratch.importance_ele_n:]: 
    statements += node.embedding_key + "\n"

  # 这里的 n 已经变为 5
  return run_gpt_prompt_focal_pt(persona, statements, n)[0]


def generate_insights_and_evidence(persona, nodes, n=8): # 改装点：由5增加到8，增强反思深度
  if debug: print ("GNS FUNCTION: <generate_insights_and_evidence>")

  statements = ""
  for count, node in enumerate(nodes): 
    statements += f'{str(count)}. {node.embedding_key}\n'

  ret = run_gpt_prompt_insight_and_guidance(persona, statements, n)[0]

  print (ret)
  try: 
    for thought, evi_raw in ret.items(): 
      evidence_node_id = [nodes[i].node_id for i in evi_raw]
      ret[thought] = evidence_node_id
    return ret
  except: 
    return {"this is blank": "node_1"} 


def generate_action_event_triple(act_desp, persona): 
  if debug: print ("GNS FUNCTION: <generate_action_event_triple>")
  return run_gpt_prompt_event_triple(act_desp, persona)[0]


def generate_poig_score(persona, event_type, description): 
    """
    核心改装：戏剧化评分系统。
    让 Agent 对冲突和社交极其敏感。
    """
    if "is idle" in description: 
        return 1

    if event_type == "event" or event_type == "thought": 
        score = run_gpt_prompt_event_poignancy(persona, description)[0]
    elif event_type == "chat": 
        score = run_gpt_prompt_chat_poignancy(persona, 
                               persona.scratch.act_description)[0]
    
    # --- 戏剧化逻辑开始 ---
    # 定义“冲突/剧情”关键词
    drama_keywords = ["secret", "suspicious", "angry", "love", "conflict", "hate", "hidden", "plan", "mystery"]
    description_lower = description.lower()
    
    # 逻辑 1：如果是对话，大幅提升基础重要性，加速反思触发
    if event_type == "chat":
        score = max(score, 6) 
        
    # 逻辑 2：如果文本包含戏剧性关键词，额外加分，确保该记忆成为“核心冲突”
    if any(kw in description_lower for kw in drama_keywords):
        score += 3
    # --- 戏剧化逻辑结束 ---
        
    return min(10, score) # 确保不超过 10 分


def generate_planning_thought_on_convo(persona, all_utt):
  if debug: print ("GNS FUNCTION: <generate_planning_thought_on_convo>")
  return run_gpt_prompt_planning_thought_on_convo(persona, all_utt)[0]


def generate_memo_on_convo(persona, all_utt):
  if debug: print ("GNS FUNCTION: <generate_memo_on_convo>")
  return run_gpt_prompt_memo_on_convo(persona, all_utt)[0]


def run_reflect(persona):
  # 每次反思生成 5 个关注点
  focal_points = generate_focal_points(persona, 5)
  retrieved = new_retrieve(persona, focal_points)

  for focal_pt, nodes in retrieved.items(): 
    # 每个关注点生成 8 个见解
    thoughts = generate_insights_and_evidence(persona, nodes, 8)
    for thought, evidence in thoughts.items(): 
      created = persona.scratch.curr_time
      expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
      s, p, o = generate_action_event_triple(thought, persona)
      keywords = set([s, p, o])
      
      # 这里会调用我们改装后的戏剧化评分
      thought_poignancy = generate_poig_score(persona, "thought", thought)
      thought_embedding_pair = (thought, get_embedding(thought))

      persona.a_mem.add_thought(created, expiration, s, p, o, 
                                thought, keywords, thought_poignancy, 
                                thought_embedding_pair, evidence)
      


def reflection_trigger(persona): 
  # 当 importance_trigger_curr 归零时触发
  if (persona.scratch.importance_trigger_curr <= 0 and 
      [] != persona.a_mem.seq_event + persona.a_mem.seq_thought): 
    return True 
  return False


def reset_reflection_counter(persona): 
    # 改装点：将触发阈值降至 60。这意味着角色每经历几次有意义的对话就会进入“深思模式”。
    dramatic_threshold = 60 
    persona.scratch.importance_trigger_max = dramatic_threshold
    
    persona.scratch.importance_trigger_curr = persona.scratch.importance_trigger_max
    persona.scratch.importance_ele_n = 0


def reflect(persona):
  if reflection_trigger(persona): 
    run_reflect(persona)
    reset_reflection_counter(persona)

  if persona.scratch.chatting_end_time: 
    if persona.scratch.curr_time + datetime.timedelta(0,10) == persona.scratch.chatting_end_time: 
      all_utt = ""
      if persona.scratch.chat: 
        for row in persona.scratch.chat:  
          all_utt += f"{row[0]}: {row[1]}\n"

      evidence = [persona.a_mem.get_last_chat(persona.scratch.chatting_with).node_id]

      planning_thought = generate_planning_thought_on_convo(persona, all_utt)
      planning_thought = f"For {persona.scratch.name}'s planning: {planning_thought}"

      created = persona.scratch.curr_time
      expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
      s, p, o = generate_action_event_triple(planning_thought, persona)
      keywords = set([s, p, o])
      
      # 增强版评分
      thought_poignancy = generate_poig_score(persona, "thought", planning_thought)
      thought_embedding_pair = (planning_thought, get_embedding(planning_thought))

      persona.a_mem.add_thought(created, expiration, s, p, o, 
                                planning_thought, keywords, thought_poignancy, 
                                thought_embedding_pair, evidence)

      memo_thought = generate_memo_on_convo(persona, all_utt)
      memo_thought = f"{persona.scratch.name} {memo_thought}"

      created = persona.scratch.curr_time
      expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
      s, p, o = generate_action_event_triple(memo_thought, persona)
      keywords = set([s, p, o])
      
      # 增强版评分
      thought_poignancy = generate_poig_score(persona, "thought", memo_thought)
      thought_embedding_pair = (memo_thought, get_embedding(memo_thought))

      persona.a_mem.add_thought(created, expiration, s, p, o, 
                                memo_thought, keywords, thought_poignancy, 
                                thought_embedding_pair, evidence)