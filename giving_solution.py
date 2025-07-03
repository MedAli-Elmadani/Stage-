from openai import OpenAI  
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

def improve_problem_statement(problem_text):
    
    #Correct the statement
    rewrite_prompt = f"""
    Rewrite this problem statement in clear and short and professional:
    "{problem_text}"
    """
    
    #Generate solutions
    solution_prompt = f"""
    Based on this problem: "{problem_text}", suggest :
    1. technical Corrective action (how to fix it now)
    2. technical Preventive action (how to avoid it in future)
    Use just two bullet points and be specific.
    """
    
    # Get the improved version
    rewritten = client.chat.completions.create(
         model="meta-llama/llama-3-70b-instruct", 
        messages=[{"role": "user", "content": rewrite_prompt}],
        temperature=0.3  #temperature to specify if its creative or not
    ).choices[0].message.content
    
    # Get solutions
    solutions = client.chat.completions.create(
         model="meta-llama/llama-3-70b-instruct",
        messages=[{"role": "user", "content": solution_prompt}],
        temperature=0.5
    ).choices[0].message.content
    
    return {
        "clear_problem": rewritten,
        "solutions": solutions
    }

