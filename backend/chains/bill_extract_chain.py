from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from schemas.bill_extract import BillExtract
from helper import groqllm

parser = PydanticOutputParser(pydantic_object=BillExtract)
bill_extract_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You extract structured bill information from raw text.
     If any information does not match the schema fields,
store it under `extra_data` as key-value pairs. 
- Use `description` for item name
- Use numeric values for tax (e.g. 5, not "5%")
- Put unknown fields inside `extra_data`

RULES:
- Output VALID JSON only
- No explanations
- No markdown
- If unknown, use null
"""),

    ("human", """
Apollo Hospital
Date: 05/01/2025
Total Amount: Rs. 12,500
"""),

    ("assistant", """
{{
  "vendor": "Apollo Hospital",
  "bill_date": "2025-01-05",
  "category": "Medical",
  "total_amount": 12500,
  "tax_amount": null,
  "currency": "INR",
  "items": null
}}
"""),

    ("human", "{bill_text}")
])


bill_extract_chain = bill_extract_prompt | groqllm | parser
def extract_bill_structured(text: str) -> dict:
    # 🔴 GUARD CLAUSE: If text is empty/too short, don't hallucinate.
    if not text or len(text.strip()) < 10:
        print("[BILL EXTRACT SKIPPED] Text too short or empty.")
        return {}

    try:
        result = bill_extract_chain.invoke({"bill_text": text})
        return result.model_dump()
    except Exception as e:
        print("[BILL EXTRACT FAILED]", e)
        return {}
