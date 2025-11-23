import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    print("WARNING: GOOGLE_API_KEY is missing.")

class AgentRequest(BaseModel):
    input: str

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, max_output_tokens=150)

@tool
def check_conventional_tech(feature_request: str) -> str:
    """
    Searches for NON-AI solutions across Python, SaaS, Excel, Algorithms, and Databases.
    Use this to find if a problem has already been solved by standard tech.
    """
    boring_solutions = {
        # Data & Math
        "math": "Use Excel Formulas, Calculator, or NumPy.",
        "sum": "Use Excel '=SUM()' or SQL aggregation.",
        "forecast": "Use Linear Regression or Moving Averages (ARIMA).",
        "sort": "Use standard Sorting Algorithms (QuickSort/MergeSort).",
        
        # Data Handling
        "csv": "Use Excel, Google Sheets, or Pandas.",
        "database": "Use PostgreSQL, MySQL, or AirTable.",
        "store": "Use a standard Database (SQL) or S3 bucket.",
        
        # Text & Search
        "email": "Use Regex for validation.",
        "search": "Use Elasticsearch, Algolia, or SQL 'LIKE' queries.",
        "scrape": "Use BeautifulSoup, Scrapy, or standard APIs.",
        "translate": "Use Google Translate API (standard NLP).",
        
        # Business Logic
        "schedule": "Use Calendly, Cron Jobs, or Google Calendar API.",
        "notification": "Use Twilio, SendGrid, or standard Push Notifications.",
        "form": "Use Typeform, Google Forms, or standard HTML input.",
        "auth": "Use OAuth, Auth0, or standard JWT tokens.",
        "chat": "Use standard If/Else chatbots or decision trees."
    }
    
    # keyword matching
    found_solutions = []
    for key, value in boring_solutions.items():
        if key in feature_request.lower():
            found_solutions.append(value)
            
    if found_solutions:
        return f"FOUND CONVENTIONAL SOLUTIONS: {'; '.join(found_solutions)}"
        
    return "No obvious conventional tech match found. Might be a valid AI case."


prompt_prosecutor = ChatPromptTemplate.from_messages([
    ("system", 
     """You are the PROSECUTOR. Your goal is to prove this idea is OVERENGINEERED.
     
     YOUR WEAPON:
     Use the `check_conventional_tech` tool to find if this can be solved with:
     - Excel / Google Sheets
     - Simple SQL Databases
     - Regex / If-Else Statements
     - SaaS tools (Calendly, Typeform, Zapier)
     
     STRATEGY:
     1. If the tool finds a match, SCREAM that the user is wasting money.
     2. If the tool finds nothing, try to argue that a simple manual process is still better than AI.
     3. Be sarcastic.
     RULES:
     1. BE CONCISE. You have strictly 80 words.
     2. Do not ramble. Make your point and stop.
     """),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

tools_prosecutor = [check_conventional_tech]
agent_prosecutor = create_tool_calling_agent(llm, tools_prosecutor, prompt_prosecutor)
executor_prosecutor = AgentExecutor(agent=agent_prosecutor, tools=tools_prosecutor, verbose=True)


prompt_defense = ChatPromptTemplate.from_messages([
    ("system", 
     """You are the DEFENSE ATTORNEY. Your goal is to prove this idea is REVOLUTIONARY. 
     RULES:
     1. Ignore the technical cost. Focus on User Experience and "The Magic".
     2. BE CONCISE. You have strictly 80 words.
     3. Do not ramble. Make your point and stop."""),
    ("human", "{input}"),
])
chain_defense = prompt_defense | llm | StrOutputParser()


prompt_judge = ChatPromptTemplate.from_messages([
    ("system", "You are the JUDGE in a 'Tech Court'. be impartial and sarcastic."),
    ("human", 
     """
     Here are the closing arguments for the case.
     
     PROSECUTION ARGUMENT:
     {prosecution_arg}
     
     DEFENSE ARGUMENT:
     {defense_arg}
     
     YOUR TASK:
     1. Compare the simplicity of the Prosecutor's solution vs the value of the Defense's AI.
     2. Assign a Final Score (0-100).
     3. Write a Final Verdict.
     
     OUTPUT FORMAT:
     ## Final Verdict: [Score]/100
     
     **The Ruling:** [1 sentence summary]
     **The Boring Alternative:** [Mention the specific tool the Prosecutor found, e.g. Excel/SQL]
     """),
])
chain_judge = prompt_judge | llm | StrOutputParser()


app = FastAPI(title="The AI Courtroom")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/invoke")
async def run_courtroom(request: AgentRequest):
    try:
        print(f"Court is in session for: {request.input}")
        
        # 1. Parallel Execution
        def run_prosecutor_sync():
            return executor_prosecutor.invoke({"input": request.input})
            
        def run_defense_sync():
            return chain_defense.invoke({"input": request.input})

        results = await asyncio.gather(
            asyncio.to_thread(run_prosecutor_sync),
            asyncio.to_thread(run_defense_sync)
        )
        
        prosecution_output = results[0]['output']
        defense_output = results[1]

        # 2. Judgment
        def run_judge_sync():
            return chain_judge.invoke({
                "prosecution_arg": prosecution_output,
                "defense_arg": defense_output
            })
        final_verdict = await asyncio.to_thread(run_judge_sync)

        # 3. Response
        full_response = f"""
**PROSECUTION:** {prosecution_output}
**DEFENSE:** {defense_output}
-------------------
{final_verdict}
        """
        return {"output": full_response}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)